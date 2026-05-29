"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM CONSENSUS INTEGRATION                               ║
║                                                                              ║
║  Pipeline d'orchestration "ResearchPipeline" : collecte multi-MCP →          ║
║  validation par consensus → clôture du dossier.                              ║
║                                                                              ║
║  ARCHITECTURE RÉELLE :                                                       ║
║                                                                              ║
║  1. COLLECTE                                                                 ║
║     ├── Firecrawl MCP ───► Données brutes (web scraping)                     ║
║     ├── Playwright MCP ──► Preuves & cas critiques                           ║
║     └── Tavily MCP ──────► Signaux faibles / orientation                     ║
║     (note : add_collection_data range les sources inconnues dans             ║
║      tavily_data par défaut — cf. ResearchDossier.add_collection_data)       ║
║                                                                              ║
║  2. ARBITRAGE                                                                ║
║     └── validate_with_consensus() délègue intégralement à                    ║
║         python.consensus.engine.run_consensus (single entrypoint v2).        ║
║                                                                              ║
║     ⚠ Les ArbiterLLM créés par _setup_arbiters() (self.arbiters) ne sont     ║
║     PLUS utilisés par validate_with_consensus depuis la migration v2.        ║
║     Ils restent instanciés pour rétrocompatibilité (cf. ADR-008) et          ║
║     consommés par les tests legacy via _collect_arbiter_vote.                ║
║                                                                              ║
║  3. INTERPRÉTATION                                                           ║
║     └── close_dossier() applique un confidence_score :                       ║
║         base = 0.9 si consensus approuvé / 0.3 si rejeté / 0.5 si bypass     ║
║         (require_consensus=False), + bonus marginal selon le nombre de       ║
║         sources collectées (plafonné à +0.05). Voir                          ║
║         `_compute_dossier_confidence` pour la formule documentée. Ces        ║
║         valeurs sont des heuristiques produit, pas un score statistique.     ║
║                                                                              ║
║  Note de naming :                                                            ║
║    ArbiterConfig (ce module) ≠ ArbiterConfig (consensus_arbiter.py). Cette   ║
║    classe a été renommée LegacyArbiterConfig pour lever l'ambiguïté.         ║
║                                                                              ║
║  "Evidence ne cherche pas, Evidence instruit un dossier."                    ║
║                                                                              ║
║  Version: 1.1.0 (post-audit hostile)                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
    build_vote_prompt,
    generate_decision_hash,
    parse_llm_vote_response,
)
from python.helpers.consensus_contracts import (
    ConsensusConfigSchema,
    ResearchDossier,
    ResearchPipelineStep,
    LLMVoteResponseSchema,
    validate_strict,
)

logger = logging.getLogger("prism_integration")


# ═══════════════════════════════════════════════════════════════════════════════
# ARBITER LLM INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LegacyArbiterConfig:
    """
    Configuration d'un modèle arbitre — version LEGACY (ResearchPipeline).
    
    DEF-ARC-3 (audit hostile 29 mai 2026) : ne pas confondre avec
    `consensus_arbiter.ArbiterConfig` (schema différent : provider/model/
    priority au lieu de name/model_id/provider). Cette classe-ci sert
    uniquement aux ArbiterLLM instanciés par ResearchPipeline._setup_arbiters,
    qui ne sont plus consommés sur le chemin actif depuis ADR-008.
    """
    name: str
    model_id: str
    provider: str
    timeout_ms: int = 5000
    temperature: float = 0.3
    max_tokens: int = 500


# Backward-compat alias (ADR-008) : ne pas casser les imports existants
# `from python.helpers.consensus_integration import ArbiterConfig`.
ArbiterConfig = LegacyArbiterConfig


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE SCORE — formule documentee (DEF-CI-2 fix)
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_dossier_confidence(
    total_sources: int,
    require_consensus: bool,
    consensus_result: Optional[Dict[str, Any]],
) -> float:
    """
    Calcule le confidence_score d'un ResearchDossier a sa cloture.
    
    DEF-CI-2 (audit hostile 29 mai 2026) : remplace les constantes magiques
    0.3 / 0.5 / 0.9 par une formule documentee et testable.
    
    Formule :
        base =
            0.3  si require_consensus=True ET consensus rejete
            0.9  si require_consensus=True ET consensus approuve
            0.5  si require_consensus=False  (bypass explicite, score median)
        
        ajustement = + min(0.05, 0.01 * total_sources)
            (bonus marginal pour la richesse des sources, plafonne a +0.05)
        
        score = clamp(base + ajustement, 0.0, 1.0)
    
    Note : ces valeurs restent des heuristiques produit ; elles n'ont pas
    vocation a etre interpretees comme une probabilite statistique. La
    pertinence du score s'evalue par les bornes (rejected < bypass <
    approved) et la monotonicite (plus de sources => score >=).
    
    Args:
        total_sources: nombre total de sources collectees dans le dossier
        require_consensus: True si consensus a ete declenche
        consensus_result: payload retourne par validate_with_consensus
                          (None si require_consensus=False)
    
    Returns:
        float dans [0.0, 1.0]
    """
    if not require_consensus:
        base = 0.5
    else:
        approved = bool(consensus_result and consensus_result.get("approved"))
        base = 0.9 if approved else 0.3
    
    sources_bonus = min(0.05, 0.01 * max(0, total_sources))
    
    raw = base + sources_bonus
    return max(0.0, min(1.0, raw))


class ArbiterLLM:
    """
    Interface pour un LLM arbitre dans le système de consensus.
    """
    
    def __init__(self, config: "LegacyArbiterConfig", call_llm_func: Callable):
        """
        Args:
            config: Configuration de l'arbitre (LegacyArbiterConfig)
            call_llm_func: Fonction pour appeler le LLM (from models.py)
        """
        self.config = config
        self.call_llm = call_llm_func
    
    async def request_vote(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> Tuple[Optional[VoteType], str, float, List[str]]:
        """
        Demande un vote à cet arbitre.
        
        Args:
            action: Description de l'action/décision à évaluer
            context: Contexte de la décision
            
        Returns:
            Tuple (vote, reasoning, confidence, risks)
        """
        prompt = build_vote_prompt(action, context)
        
        try:
            # Appeler le LLM
            response = await asyncio.wait_for(
                self._call_model(prompt),
                timeout=self.config.timeout_ms / 1000
            )
            
            # Parser la réponse
            parsed = parse_llm_vote_response(response)
            
            vote = VoteType.APPROVE if parsed["approve"] else VoteType.REJECT
            return (
                vote,
                parsed["reasoning"],
                parsed.get("confidence", 0.5),
                parsed.get("risks_identified", [])
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Timeout pour arbitre {self.config.name}")
            return (None, "Timeout", 0.0, [])
            
        except Exception as e:
            # FAIL-CLOSED : Erreur = UNAVAILABLE
            logger.error(f"❌ Erreur arbitre {self.config.name}: {e}")
            return (None, f"Error: {str(e)}", 0.0, [])
    
    async def _call_model(self, prompt: str) -> str:
        """Appelle le modèle LLM."""
        # Cette méthode sera connectée au système de modèles d'Evidence
        # Pour l'instant, structure de base
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.call_llm(
            model=self.config.model_id,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchPipeline:
    """
    Pipeline de recherche avec collecte MCP et validation par consensus.
    
    "Evidence ne cherche pas, Evidence instruit un dossier."
    """
    
    def __init__(
        self,
        consensus_config: ConsensusConfigSchema,
        mcp_handler: Any = None,  # MCPConfig instance
        call_llm_func: Callable = None
    ):
        self.config = consensus_config
        self.mcp_handler = mcp_handler
        self.call_llm = call_llm_func
        
        # Initialiser le consensus manager
        self.consensus = ConsensusManager(
            timeout_ms=consensus_config.timeout_ms,
            total_providers=consensus_config.total_providers
        )
        
        # Configurer les arbitres
        self.arbiters: List[ArbiterLLM] = []
        if call_llm_func:
            self._setup_arbiters()
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        
        # Setup event listeners
        self._setup_listeners()
    
    def _setup_arbiters(self):
        """
        [LEGACY ADR-008] Instancie 3 ArbiterLLM legacy.
        
        Ces arbitres NE SONT PLUS consommés par `validate_with_consensus` qui
        délègue à `engine.run_consensus`. Conservés uniquement pour les chemins
        legacy (_collect_arbiter_vote) et la rétro-compatibilité des tests.
        """
        arbiter_configs = [
            LegacyArbiterConfig(
                name="Arbiter_1",
                model_id=self.config.arbiter_model_1,
                provider="primary"
            ),
            LegacyArbiterConfig(
                name="Arbiter_2",
                model_id=self.config.arbiter_model_2,
                provider="secondary"
            ),
            LegacyArbiterConfig(
                name="Arbiter_3",
                model_id=self.config.arbiter_model_3,
                provider="tertiary"
            ),
        ]
        
        for config in arbiter_configs:
            self.arbiters.append(ArbiterLLM(config, self.call_llm))
    
    def _setup_listeners(self):
        """Configure les listeners d'événements."""
        self.consensus.on("consensus_reached", self._on_consensus_reached)
        self.consensus.on("consensus_timeout", self._on_consensus_timeout)
        self.consensus.on("vote_submitted", self._on_vote_submitted)
    
    def _on_consensus_reached(self, data: Dict[str, Any]):
        """Handler pour consensus atteint."""
        self._log_audit("consensus_reached", data)
        emoji = "✅" if data["status"] == "APPROVED" else "❌"
        logger.info(f"{emoji} Consensus final: {data['status']}")
    
    def _on_consensus_timeout(self, data: Dict[str, Any]):
        """Handler pour timeout."""
        self._log_audit("consensus_timeout", data)
        logger.warning(f"⏰ Consensus timeout: {data['proposal_id'][:8]}...")
    
    def _on_vote_submitted(self, data: Dict[str, Any]):
        """Handler pour vote soumis."""
        if self.config.log_votes:
            self._log_audit("vote_submitted", data)
    
    def _log_audit(self, event_type: str, data: Dict[str, Any]):
        """Ajoute une entrée au log d'audit."""
        if self.config.enable_audit_log:
            entry = {
                "timestamp": time.time(),
                "event_type": event_type,
                **data
            }
            self.audit_log.append(entry)
    
    async def open_dossier(self, query: str) -> ResearchDossier:
        """
        Ouvre un nouveau dossier de recherche.
        
        Args:
            query: Requête de recherche
            
        Returns:
            ResearchDossier initialisé
        """
        dossier = ResearchDossier(
            dossier_id=str(uuid.uuid4()),
            query=query,
            created_at=time.time()
        )
        
        logger.info(f"📂 Dossier ouvert: {dossier.dossier_id[:8]}...")
        self._log_audit("dossier_opened", {"dossier_id": dossier.dossier_id, "query": query})
        
        return dossier
    
    async def collect_data(
        self,
        dossier: ResearchDossier,
        sources: List[str] = None
    ) -> ResearchDossier:
        """
        Collecte les données depuis les MCP servers.
        
        Args:
            dossier: Dossier de recherche
            sources: Liste des sources ("firecrawl", "playwright", "tavily")
            
        Returns:
            Dossier mis à jour avec les données
        """
        if sources is None:
            sources = ["firecrawl", "tavily", "playwright"]
        
        logger.info(f"🔍 Collecte de données pour: {dossier.query}")
        
        # Collecter en parallèle depuis chaque source
        tasks = []
        for source in sources:
            task = asyncio.create_task(
                self._collect_from_source(dossier, source)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return dossier
    
    async def _collect_from_source(
        self,
        dossier: ResearchDossier,
        source: str
    ) -> None:
        """Collecte depuis une source MCP spécifique."""
        step = ResearchPipelineStep(
            step_id=str(uuid.uuid4()),
            step_name=f"collect_{source}",
            mcp_server=source,
            input_query=dossier.query,
            start_time=time.time()
        )
        dossier.collection_steps.append(step)
        
        try:
            step.status = "running"
            
            # Appeler le MCP server approprié
            if self.mcp_handler:
                data = await self._call_mcp(source, dossier.query)
                step.output_data = data
                dossier.add_collection_data(source, data)
            else:
                # Mode simulation si pas de MCP handler
                step.output_data = {"simulated": True, "source": source}
            
            step.status = "completed"
            step.end_time = time.time()
            
            logger.info(f"  ✓ {source}: {step.duration_ms}ms")
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.end_time = time.time()
            logger.error(f"  ✗ {source}: {e}")
    
    async def _call_mcp(self, server: str, query: str) -> Dict[str, Any]:
        """Appelle un serveur MCP pour collecter des données."""
        if not self.mcp_handler:
            return {"error": "No MCP handler configured"}
        
        # Mapping des outils par serveur
        tool_mapping = {
            "firecrawl": ("firecrawl", "scrape"),
            "playwright": ("playwright", "navigate"),
            "tavily": ("tavily", "search"),
        }
        
        server_name, tool_name = tool_mapping.get(server, (server, "search"))
        
        try:
            result = await self.mcp_handler.call_tool(
                server_name,
                tool_name,
                {"query": query}
            )
            return {"result": result, "source": server}
        except Exception as e:
            return {"error": str(e), "source": server}
    
    async def validate_with_consensus(
        self,
        dossier: ResearchDossier,
        conclusion: str,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Valide une conclusion par consensus multi-LLM.
        
        Args:
            dossier: Dossier de recherche
            conclusion: Conclusion à valider
            context: Contexte additionnel
            
        Returns:
            Tuple (approved, result_details)
        """
        logger.info("🔒 Validation par consensus (engine)...")
        from python.consensus.engine import run_consensus

        full_context = {
            "dossier_id": dossier.dossier_id,
            "query": dossier.query,
            "data_sources": len(dossier.get_all_data()),
            "firecrawl_count": len(dossier.firecrawl_data),
            "playwright_count": len(dossier.playwright_data),
            "tavily_count": len(dossier.tavily_data),
            **(context or {}),
        }

        decision = await run_consensus(
            evidence_pack={"dossier_id": dossier.dossier_id, "data": dossier.get_all_data()},
            policy={
                "action": conclusion,
                "context": full_context,
                "decision_type": DecisionType.RESEARCH_VALIDATION,
                "correlation_id": dossier.dossier_id,
            },
        )

        result = {
            "proposal_id": decision.proposal_id,
            "approved": decision.approved,
            "status": decision.status.value,
            "votes": {k: v.__dict__ for k, v in decision.votes.items()},
            "decision_hash": decision.decision_hash,
            "decision_time_ms": decision.decision_time_ms,
            "warnings": decision.warnings,
        }

        dossier.consensus_results.append(result)

        return decision.approved, result
    
    async def _collect_arbiter_vote(
        self,
        arbiter: ArbiterLLM,
        proposal_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> None:
        """Collecte le vote d'un arbitre."""
        vote, reasoning, confidence, risks = await arbiter.request_vote(action, context)
        
        self.consensus.submit_vote(
            proposal_id,
            arbiter.config.name,
            vote,
            reasoning,
            confidence,
            risks
        )
    
    async def close_dossier(
        self,
        dossier: ResearchDossier,
        final_conclusion: str,
        require_consensus: bool = True
    ) -> ResearchDossier:
        """
        Clôture un dossier avec validation finale.
        
        Args:
            dossier: Dossier à clôturer
            final_conclusion: Conclusion finale
            require_consensus: Si True, valide par consensus
            
        Returns:
            Dossier clôturé
        """
        consensus_result = None
        if require_consensus:
            dossier.status = "validating"
            approved, consensus_result = await self.validate_with_consensus(
                dossier,
                final_conclusion
            )
            
            if not approved:
                logger.warning("⚠️ Conclusion non validée par consensus")
        
        dossier.confidence_score = _compute_dossier_confidence(
            total_sources=len(dossier.get_all_data()),
            require_consensus=require_consensus,
            consensus_result=consensus_result,
        )
        
        dossier.final_conclusion = final_conclusion
        dossier.status = "closed"
        
        logger.info(f"📁 Dossier clôturé: {dossier.dossier_id[:8]}...")
        self._log_audit("dossier_closed", {
            "dossier_id": dossier.dossier_id,
            "conclusion": final_conclusion[:100],
            "confidence": dossier.confidence_score
        })
        
        return dossier
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Retourne le log d'audit complet."""
        return self.audit_log.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques du consensus."""
        return self.consensus.metrics.copy()


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def create_research_pipeline(
    config: Dict[str, Any] = None,
    mcp_handler: Any = None,
    call_llm_func: Callable = None
) -> ResearchPipeline:
    """
    Crée une instance du pipeline de recherche.
    
    Args:
        config: Configuration du consensus (optionnel)
        mcp_handler: Handler MCP pour les appels aux serveurs
        call_llm_func: Fonction pour appeler les LLMs
        
    Returns:
        ResearchPipeline configuré
    """
    if config is None:
        config = {}
    
    consensus_config = ConsensusConfigSchema(**config)
    
    return ResearchPipeline(
        consensus_config=consensus_config,
        mcp_handler=mcp_handler,
        call_llm_func=call_llm_func
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ═══════════════════════════════════════════════════════════════════════════════

async def example_usage():
    """Exemple d'utilisation du pipeline."""
    
    # Créer le pipeline
    pipeline = create_research_pipeline(
        config={
            "timeout_ms": 10000,
            "total_providers": 3,
            "arbiter_model_1": "openrouter/anthropic/claude-3.5-sonnet",
            "arbiter_model_2": "openrouter/openai/gpt-4o",
            "arbiter_model_3": "openrouter/google/gemini-pro-1.5",
        }
    )
    
    # Ouvrir un dossier
    dossier = await pipeline.open_dossier(
        "Recherche sur les architectures Transformer pour brevets IA"
    )
    
    # Collecter les données
    dossier = await pipeline.collect_data(
        dossier,
        sources=["firecrawl", "tavily", "playwright"]
    )
    
    # Valider une conclusion
    approved, result = await pipeline.validate_with_consensus(
        dossier,
        "Les architectures Transformer modernes présentent une activité inventive suffisante pour un dépôt de brevet.",
        context={"domain": "AI/ML", "jurisdiction": "INPI"}
    )
    
    print(f"Consensus: {'APPROVED' if approved else 'REJECTED'}")
    print(f"Détails: {result}")
    
    # Clôturer le dossier
    dossier = await pipeline.close_dossier(
        dossier,
        "Conclusion finale du dossier de recherche.",
        require_consensus=True
    )
    
    return dossier


if __name__ == "__main__":
    asyncio.run(example_usage())

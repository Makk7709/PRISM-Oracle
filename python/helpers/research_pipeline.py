"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     EVIDENCE RESEARCH PIPELINE                                 ║
║                                                                              ║
║  Pipeline de recherche complet avec :                                        ║
║  - Firecrawl MCP → collecte brute (web scraping)                            ║
║  - Playwright MCP → preuves & cas critiques                                  ║
║  - Tavily MCP → signaux faibles / orientation                                ║
║  - PRISM Consensus → arbitrage multi-LLM                                     ║
║  - Evidence ReasoningEngine → interprétation finale                            ║
║                                                                              ║
║  "Evidence ne cherche pas, Evidence instruit un dossier."                        ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
    build_vote_prompt,
    generate_decision_hash,
    is_critical_action,
)
from python.helpers.consensus_contracts import (
    ConsensusConfigSchema,
    ResearchDossier,
    ResearchPipelineStep,
)

logger = logging.getLogger("evidence_pipeline")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class DataSource(str, Enum):
    """Sources de données MCP."""
    FIRECRAWL = "firecrawl"
    PLAYWRIGHT = "playwright"
    TAVILY = "tavily"
    ARXIV = "arxiv"
    SEMANTICSCHOLAR = "semanticscholar"
    OPENALEX = "openalex"


class PipelineStage(str, Enum):
    """Étapes du pipeline."""
    COLLECTION = "collection"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    CONCLUSION = "conclusion"


# Configuration par défaut des sources
SOURCE_TOOLS = {
    DataSource.FIRECRAWL: {
        "tool": "scrape",
        "priority": 1,
        "description": "Collecte brute de données web"
    },
    DataSource.PLAYWRIGHT: {
        "tool": "navigate",
        "priority": 2,
        "description": "Preuves & cas critiques (interactions)"
    },
    DataSource.TAVILY: {
        "tool": "search",
        "priority": 3,
        "description": "Signaux faibles & orientation"
    },
    DataSource.ARXIV: {
        "tool": "search",
        "priority": 4,
        "description": "Recherche académique arXiv"
    },
    DataSource.SEMANTICSCHOLAR: {
        "tool": "search_papers",
        "priority": 5,
        "description": "Recherche Semantic Scholar"
    },
    DataSource.OPENALEX: {
        "tool": "search_works",
        "priority": 6,
        "description": "Recherche OpenAlex"
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# TASK DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchTask:
    """Tâche de recherche décomposée."""
    id: str
    query: str
    parent_id: Optional[str] = None
    subtasks: List["ResearchTask"] = field(default_factory=list)
    sources: List[DataSource] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def is_atomic(self) -> bool:
        """Vérifie si la tâche est atomique (pas de sous-tâches)."""
        return len(self.subtasks) == 0


class TaskDecomposer:
    """
    Décompose une requête de recherche complexe en tâches gérables.
    
    Principe : Chaque tâche doit être indépendamment exécutable et vérifiable.
    """
    
    def __init__(self, call_llm_func: Callable = None):
        self.call_llm = call_llm_func
    
    async def decompose(self, query: str, max_depth: int = 2) -> ResearchTask:
        """
        Décompose une requête en tâches hiérarchiques.
        
        Args:
            query: Requête de recherche
            max_depth: Profondeur maximale de décomposition
            
        Returns:
            ResearchTask racine avec sous-tâches
        """
        root_task = ResearchTask(
            id=str(uuid.uuid4()),
            query=query,
            sources=self._identify_sources(query)
        )
        
        # Décomposition si le LLM est disponible et requête complexe
        if self.call_llm and self._is_complex_query(query):
            subtasks = await self._decompose_with_llm(query, max_depth)
            root_task.subtasks = subtasks
        
        return root_task
    
    def _is_complex_query(self, query: str) -> bool:
        """Détermine si une requête nécessite décomposition."""
        complex_indicators = [
            " et ", " ou ", " puis ", " ensuite ",
            "comparer", "analyser", "évaluer", "valider",
            "multiple", "plusieurs", "différent"
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in complex_indicators)
    
    def _identify_sources(self, query: str) -> List[DataSource]:
        """Identifie les sources pertinentes pour une requête."""
        sources = []
        query_lower = query.lower()
        
        # Mapping keywords -> sources
        source_keywords = {
            DataSource.ARXIV: ["paper", "article", "recherche", "scientifique", "arxiv"],
            DataSource.SEMANTICSCHOLAR: ["citation", "auteur", "publication", "académique"],
            DataSource.OPENALEX: ["journal", "revue", "institution", "concept"],
            DataSource.FIRECRAWL: ["site", "page", "web", "url", "scrape"],
            DataSource.PLAYWRIGHT: ["interaction", "formulaire", "click", "preuve"],
            DataSource.TAVILY: ["actualité", "news", "tendance", "récent"],
        }
        
        for source, keywords in source_keywords.items():
            if any(kw in query_lower for kw in keywords):
                sources.append(source)
        
        # Default : academic sources + tavily for orientation
        if not sources:
            sources = [DataSource.ARXIV, DataSource.SEMANTICSCHOLAR, DataSource.TAVILY]
        
        return sources
    
    async def _decompose_with_llm(
        self, 
        query: str, 
        max_depth: int
    ) -> List[ResearchTask]:
        """Décompose une requête en utilisant un LLM."""
        if not self.call_llm:
            return []
        
        prompt = f"""Tu es un expert en décomposition de tâches de recherche.
Décompose cette requête de recherche en sous-tâches atomiques et exécutables.

Requête: {query}

Réponds avec un JSON:
{{
  "subtasks": [
    {{"query": "sous-tâche 1", "sources": ["arxiv", "semanticscholar"]}},
    {{"query": "sous-tâche 2", "sources": ["tavily"]}}
  ]
}}

Chaque sous-tâche doit être:
- Indépendante et vérifiable
- Spécifique (pas de requête vague)
- Associée aux bonnes sources de données
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(response)
            
            subtasks = []
            for st in parsed.get("subtasks", []):
                task = ResearchTask(
                    id=str(uuid.uuid4()),
                    query=st["query"],
                    sources=[DataSource(s) for s in st.get("sources", ["tavily"])]
                )
                subtasks.append(task)
            
            return subtasks
        except Exception as e:
            logger.warning(f"Échec décomposition LLM: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceResearchPipeline:
    """
    Pipeline de recherche complet avec consensus multi-LLM.
    
    Architecture:
    1. COLLECTE: Firecrawl → Playwright → Tavily → Academic
    2. ARBITRAGE: PRISM Consensus (3 LLMs)
    3. INTERPRÉTATION: ReasoningEngine
    """
    
    def __init__(
        self,
        mcp_handler: Any = None,
        call_llm_func: Callable = None,
        settings: Dict[str, Any] = None
    ):
        self.mcp_handler = mcp_handler
        self.call_llm = call_llm_func
        self.settings = settings or {}
        
        # Configuration consensus
        consensus_config = ConsensusConfigSchema(
            enabled=self.settings.get("consensus_enabled", True),
            timeout_ms=self.settings.get("consensus_timeout_ms", 10000),
            quorum_ratio=self.settings.get("consensus_quorum_ratio", 0.67),
            arbiter_model_1=self.settings.get("consensus_arbiter_1", "openrouter/anthropic/claude-3.5-sonnet"),
            arbiter_model_2=self.settings.get("consensus_arbiter_2", "openrouter/openai/gpt-4o"),
            arbiter_model_3=self.settings.get("consensus_arbiter_3", "openrouter/google/gemini-pro-1.5"),
            enable_audit_log=self.settings.get("consensus_audit_log", True),
        )
        
        self.consensus = ConsensusManager(
            timeout_ms=consensus_config.timeout_ms,
            total_providers=3
        )
        
        self.decomposer = TaskDecomposer(call_llm_func)
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        
        # Active dossiers
        self.dossiers: Dict[str, ResearchDossier] = {}
    
    async def research(
        self,
        query: str,
        sources: List[str] = None,
        require_consensus: bool = True
    ) -> Dict[str, Any]:
        """
        Exécute une recherche complète avec dossier.
        
        Args:
            query: Requête de recherche
            sources: Sources à utiliser (default: auto)
            require_consensus: Valider par consensus
            
        Returns:
            Résultat de la recherche avec dossier
        """
        logger.info(f"🔍 Nouvelle recherche: {query[:50]}...")
        
        # 1. Ouvrir dossier
        dossier = await self._open_dossier(query)
        
        # 2. Décomposer la tâche
        task = await self.decomposer.decompose(query)
        
        # 3. Collecter les données
        await self._collect_data(dossier, task, sources)
        
        # 4. Analyser et synthétiser
        analysis = await self._analyze_data(dossier)
        
        # 5. Valider par consensus si requis
        if require_consensus and self.settings.get("consensus_enabled", True):
            approved, consensus_result = await self._validate_consensus(
                dossier, analysis
            )
            dossier.consensus_results.append(consensus_result)
        else:
            approved = True
            consensus_result = {"status": "SKIPPED", "reason": "Consensus disabled"}
        
        # 6. Générer conclusion finale
        conclusion = await self._generate_conclusion(dossier, analysis, approved)
        
        # 7. Clôturer dossier
        dossier.final_conclusion = conclusion
        dossier.status = "closed"
        dossier.confidence_score = 0.9 if approved else 0.3
        
        return {
            "dossier_id": dossier.dossier_id,
            "query": query,
            "conclusion": conclusion,
            "approved": approved,
            "consensus": consensus_result,
            "data_collected": len(dossier.get_all_data()),
            "confidence": dossier.confidence_score
        }
    
    async def _open_dossier(self, query: str) -> ResearchDossier:
        """Ouvre un nouveau dossier de recherche."""
        dossier = ResearchDossier(
            dossier_id=str(uuid.uuid4()),
            query=query,
            created_at=time.time()
        )
        self.dossiers[dossier.dossier_id] = dossier
        
        self._log_audit("dossier_opened", {
            "dossier_id": dossier.dossier_id,
            "query": query
        })
        
        return dossier
    
    async def _collect_data(
        self,
        dossier: ResearchDossier,
        task: ResearchTask,
        sources: List[str] = None
    ):
        """Collecte les données depuis les MCPs."""
        # Déterminer les sources à utiliser
        if sources:
            task_sources = [DataSource(s) for s in sources if s in DataSource.__members__.values()]
        else:
            task_sources = task.sources
        
        # Ajouter les sources de collecte prioritaires
        if DataSource.FIRECRAWL not in task_sources:
            task_sources.insert(0, DataSource.FIRECRAWL)
        if DataSource.TAVILY not in task_sources:
            task_sources.append(DataSource.TAVILY)
        
        # Collecter en parallèle
        tasks = []
        for source in task_sources:
            step = ResearchPipelineStep(
                step_id=str(uuid.uuid4()),
                step_name=f"collect_{source.value}",
                mcp_server=source.value,
                input_query=task.query,
                start_time=time.time()
            )
            dossier.collection_steps.append(step)
            tasks.append(self._collect_from_source(dossier, source, step))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Erreur collecte {task_sources[i]}: {result}")
    
    async def _collect_from_source(
        self,
        dossier: ResearchDossier,
        source: DataSource,
        step: ResearchPipelineStep
    ):
        """Collecte depuis une source MCP."""
        step.status = "running"
        
        try:
            if self.mcp_handler:
                tool_config = SOURCE_TOOLS.get(source, {})
                tool_name = tool_config.get("tool", "search")
                
                result = await self.mcp_handler.call_tool(
                    source.value,
                    tool_name,
                    {"query": dossier.query}
                )
                
                step.output_data = result
                dossier.add_collection_data(source.value, {
                    "source": source.value,
                    "data": result,
                    "timestamp": time.time()
                })
            else:
                # Mode simulation
                step.output_data = {"simulated": True, "source": source.value}
            
            step.status = "completed"
            step.end_time = time.time()
            logger.info(f"  ✓ {source.value}: {step.duration_ms}ms")
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.end_time = time.time()
            logger.error(f"  ✗ {source.value}: {e}")
    
    async def _analyze_data(self, dossier: ResearchDossier) -> Dict[str, Any]:
        """Analyse et synthétise les données collectées."""
        all_data = dossier.get_all_data()
        
        if not self.call_llm:
            return {
                "summary": "Analyse non disponible (pas de LLM configuré)",
                "data_count": len(all_data),
                "sources": list(set(d.get("source", "unknown") for d in all_data))
            }
        
        # Construire le prompt d'analyse
        prompt = f"""Tu es un analyste de recherche expert.
Analyse les données suivantes et produis une synthèse structurée.

## Requête de recherche
{dossier.query}

## Données collectées ({len(all_data)} sources)
{json.dumps(all_data[:10], indent=2, ensure_ascii=False)}  # Limiter pour le contexte

## Instructions
Produis une analyse structurée avec:
1. Points clés identifiés
2. Sources les plus pertinentes
3. Lacunes dans les données
4. Niveau de confiance

Réponds en JSON:
{{
  "key_findings": ["point 1", "point 2"],
  "best_sources": ["source 1", "source 2"],
  "data_gaps": ["lacune 1"],
  "confidence": 0.0-1.0,
  "summary": "Synthèse en 2-3 phrases"
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Erreur analyse: {e}")
            return {
                "summary": f"Erreur d'analyse: {e}",
                "data_count": len(all_data),
                "confidence": 0.3
            }
    
    async def _validate_consensus(
        self,
        dossier: ResearchDossier,
        analysis: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Valide l'analyse par consensus multi-LLM."""
        logger.info("🔒 Validation par consensus (engine)...")
        from python.consensus.engine import run_consensus

        context = {
            "dossier_id": dossier.dossier_id,
            "query": dossier.query,
            "data_count": len(dossier.get_all_data()),
            "analysis": analysis,
        }

        decision = await run_consensus(
            evidence_pack={"dossier_id": dossier.dossier_id, "data": dossier.get_all_data()},
            policy={
                "action": analysis.get("summary", ""),
                "context": context,
                "decision_type": DecisionType.RESEARCH_VALIDATION,
                "correlation_id": dossier.dossier_id,
            },
        )

        result = {
            "proposal_id": decision.proposal_id,
            "status": decision.status.value,
            "votes": {k: v.__dict__ for k, v in decision.votes.items()},
            "approved": decision.approved,
            "decision_time_ms": decision.decision_time_ms,
            "warnings": decision.warnings,
        }

        return decision.approved, result
    
    async def _generate_conclusion(
        self,
        dossier: ResearchDossier,
        analysis: Dict[str, Any],
        approved: bool
    ) -> str:
        """Génère la conclusion finale du dossier."""
        if not self.call_llm:
            return analysis.get("summary", "Conclusion non disponible")
        
        status_text = "VALIDÉ par consensus" if approved else "NON VALIDÉ - révision recommandée"
        
        prompt = f"""Tu es l'Evidence ReasoningEngine.
Génère la conclusion finale de ce dossier de recherche.

## Requête
{dossier.query}

## Analyse
{json.dumps(analysis, indent=2, ensure_ascii=False)}

## Statut consensus
{status_text}

## Instructions
Rédige une conclusion finale qui:
1. Répond à la requête originale
2. Cite les sources les plus fiables
3. Mentionne le niveau de confiance
4. Indique si des recherches supplémentaires sont nécessaires

La conclusion doit être professionnelle et objective.
"""
        
        try:
            conclusion = await self.call_llm(prompt)
            return conclusion
        except Exception as e:
            return f"Conclusion: {analysis.get('summary', 'Erreur')} [Confiance: {analysis.get('confidence', 'N/A')}]"
    
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
        if require_consensus and self.settings.get("consensus_enabled", True):
            dossier.status = "validating"
            approved, result = await self._validate_consensus(
                dossier,
                {"summary": final_conclusion, "confidence": 0.7}
            )
            
            if not approved:
                logger.warning("⚠️ Conclusion non validée par consensus")
                dossier.confidence_score = 0.3
            else:
                dossier.confidence_score = 0.9
        else:
            dossier.confidence_score = 0.5
        
        dossier.final_conclusion = final_conclusion
        dossier.status = "closed"
        
        logger.info(f"📁 Dossier clôturé: {dossier.dossier_id[:8]}...")
        self._log_audit("dossier_closed", {
            "dossier_id": dossier.dossier_id,
            "conclusion": final_conclusion[:100],
            "confidence": dossier.confidence_score
        })
        
        return dossier
    
    def _log_audit(self, event_type: str, data: Dict[str, Any]):
        """Ajoute une entrée au log d'audit."""
        entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            **data
        }
        self.audit_log.append(entry)
    
    def get_dossier(self, dossier_id: str) -> Optional[ResearchDossier]:
        """Récupère un dossier par son ID."""
        return self.dossiers.get(dossier_id)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Retourne le log d'audit."""
        return self.audit_log.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques du pipeline."""
        return {
            "consensus_metrics": self.consensus.metrics,
            "total_dossiers": len(self.dossiers),
            "audit_entries": len(self.audit_log)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def create_pipeline(
    mcp_handler: Any = None,
    call_llm_func: Callable = None,
    settings: Dict[str, Any] = None
) -> EvidenceResearchPipeline:
    """
    Factory pour créer un pipeline de recherche.
    
    Args:
        mcp_handler: Handler MCP
        call_llm_func: Fonction d'appel LLM
        settings: Settings Evidence
        
    Returns:
        EvidenceResearchPipeline configuré
    """
    return EvidenceResearchPipeline(
        mcp_handler=mcp_handler,
        call_llm_func=call_llm_func,
        settings=settings or {}
    )

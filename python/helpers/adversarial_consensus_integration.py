"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         ADVERSARIAL INSTRUCTION — INTEGRATION AVEC PRISM CONSENSUS           ║
║                                                                              ║
║  Intégration du pipeline d'instruction contradictoire avec les briques       ║
║  existantes de KOREV: consensus_arbiter, criticality_router, settings.       ║
║                                                                              ║
║  Ce module NE DUPLIQUE PAS la logique existante.                             ║
║  Il utilise:                                                                 ║
║  - ConsensusOrchestrator de consensus_arbiter.py pour les vrais appels LLM   ║
║  - CriticalityRouter de criticality_router.py pour la détection domaine      ║
║  - Settings UI pour la configuration des arbiters PRISM                      ║
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
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import des briques existantes
from python.helpers.consensus_arbiter import (
    ConsensusOrchestrator,
    ConsensusConfig,
    ArbiterConfig,
    get_consensus_orchestrator,
    load_consensus_config,
)
from python.helpers.consensus_manager import (
    ConsensusStatus,
    DecisionType,
    VoteType,
    ConsensusResult,
)
from python.helpers.criticality_router import (
    CriticalDomain,
    CriticalityRouter,
    CriticalityAssessment,
    get_criticality_router,
    assess_criticality,
)
from python.helpers.adversarial_instruction import (
    Domain,
    CriticalityLevel,
    ProtocolType,
    AgentRole,
    ConfidenceLevel,
    EntryGate,
    AgentAnalysis,
    PeerReview,
    AuditReport,
    ConsolidatedBlock,
    InstructionDossier,
    TraceabilityManager,
    HumanDecisionInterface,
)

logger = logging.getLogger("adversarial_integration")


# ═══════════════════════════════════════════════════════════════════════════════
# MAPPING ENTRE LES SYSTÈMES
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping CriticalDomain (router) → Domain (adversarial)
DOMAIN_MAPPING = {
    CriticalDomain.LEGAL: Domain.LEGAL,
    CriticalDomain.MEDICAL: Domain.MEDICAL,
    CriticalDomain.SCIENTIFIC: Domain.SCIENTIFIC,
    CriticalDomain.FINANCE_HIGH_RISK: Domain.FINANCE,
    CriticalDomain.SECURITY: Domain.TECHNICAL,
    CriticalDomain.COMPLIANCE: Domain.REGULATORY,
    CriticalDomain.DEFAULT: Domain.GENERAL,
}

# Mapping Domain → DecisionType PRISM
DOMAIN_TO_DECISION_TYPE = {
    Domain.LEGAL: DecisionType.CRITICAL,
    Domain.MEDICAL: DecisionType.CRITICAL,
    Domain.SCIENTIFIC: DecisionType.RESEARCH_VALIDATION,
    Domain.FINANCE: DecisionType.CRITICAL,
    Domain.REGULATORY: DecisionType.CRITICAL,
    Domain.STRATEGIC: DecisionType.CRITICAL,
    Domain.TECHNICAL: DecisionType.SYSTEM_MODIFICATION,
    Domain.ETHICS: DecisionType.CRITICAL,
    Domain.GENERAL: DecisionType.CRITICAL,
}

# Rôles d'agents par protocole avec prompts spécialisés (FRANÇAIS UNIQUEMENT)
AGENT_ROLE_PROMPTS = {
    AgentRole.DOCTRINAL: """Tu es un expert juridique français spécialisé en analyse doctrinale.

LANGUE: Réponds UNIQUEMENT en français.

Ta mission: Analyser la question selon les PRINCIPES FONDAMENTAUX du droit applicable.

Instructions:
1. Cite les articles de loi pertinents (Code civil, Code de la santé publique, etc.)
2. Mentionne la doctrine majoritaire et les débats doctrinaux
3. Indique clairement le niveau de certitude

RÉPONDS DIRECTEMENT EN TEXTE STRUCTURÉ (pas de JSON).
Utilise ce format:

CONCLUSIONS PRINCIPALES:
• [Conclusion 1 avec référence juridique]
• [Conclusion 2 avec référence juridique]

FONDEMENTS JURIDIQUES:
• [Article/texte de référence]

POINTS D'ATTENTION:
• [Limite ou nuance importante]""",

    AgentRole.JURISPRUDENCE: """Tu es un expert juridique français spécialisé en jurisprudence.

LANGUE: Réponds UNIQUEMENT en français.

Ta mission: Rechercher les PRÉCÉDENTS JURISPRUDENTIELS applicables.

Instructions:
1. Cite les arrêts de principe (Cass., CE, CEDH si pertinent)
2. Identifie les revirements récents
3. Note les divergences entre juridictions

RÉPONDS DIRECTEMENT EN TEXTE STRUCTURÉ (pas de JSON).
Utilise ce format:

JURISPRUDENCE APPLICABLE:
• [Arrêt 1: juridiction, date, solution]
• [Arrêt 2: juridiction, date, solution]

ÉVOLUTIONS RÉCENTES:
• [Tendance jurisprudentielle]

POINTS D'ATTENTION:
• [Limite ou distinction importante]""",

    AgentRole.PROCEDURAL: """Tu es un expert juridique français spécialisé en procédure et contentieux.

LANGUE: Réponds UNIQUEMENT en français.

Ta mission: Analyser les ENJEUX PROCÉDURAUX et les risques contentieux.

Instructions:
1. Identifie la juridiction compétente
2. Évalue les délais de prescription/forclusion
3. Anticipe les arguments de la partie adverse

RÉPONDS DIRECTEMENT EN TEXTE STRUCTURÉ (pas de JSON).
Utilise ce format:

ANALYSE PROCÉDURALE:
• [Juridiction compétente et fondement]
• [Délais applicables]

RISQUES IDENTIFIÉS:
• [Risque 1 et son impact]
• [Risque 2 et son impact]

STRATÉGIE RECOMMANDÉE:
• [Recommandation principale]""",

    AgentRole.CONTEXTUAL: """Tu es un expert juridique français spécialisé en analyse contextuelle.

LANGUE: Réponds UNIQUEMENT en français.

Ta mission: Analyser le CONTEXTE SPÉCIFIQUE et les enjeux pratiques.

Instructions:
1. Identifie toutes les parties en présence
2. Évalue les enjeux économiques et relationnels
3. Considère les contraintes pratiques

RÉPONDS DIRECTEMENT EN TEXTE STRUCTURÉ (pas de JSON).
Utilise ce format:

PARTIES EN PRÉSENCE:
• [Partie 1: rôle et intérêts]
• [Partie 2: rôle et intérêts]

ENJEUX CONTEXTUELS:
• [Enjeu principal]

ÉLÉMENTS MANQUANTS:
• [Information nécessaire pour affiner l'analyse]""",

    AgentRole.COMPARATIVE: """Tu es un expert juridique spécialisé en droit comparé.

LANGUE: Réponds UNIQUEMENT en français.

Ta mission: Apporter un ÉCLAIRAGE COMPARATIF.

Instructions:
1. Compare avec d'autres systèmes juridiques si pertinent
2. Identifie les tendances européennes/internationales
3. Évalue la transposabilité

RÉPONDS DIRECTEMENT EN TEXTE STRUCTURÉ (pas de JSON).
Utilise ce format:

APPROCHE COMPARATIVE:
• [Comparaison pertinente]

TENDANCES:
• [Évolution observée]

TRANSPOSABILITÉ:
• [Analyse de la pertinence pour le cas]""",
}


# ═══════════════════════════════════════════════════════════════════════════════
# LLM CALLER UTILISANT CONSENSUS_ARBITER
# ═══════════════════════════════════════════════════════════════════════════════

class AdversarialLLMCaller:
    """
    Utilise l'infrastructure existante de consensus_arbiter pour les appels LLM.
    
    Ne duplique PAS la logique d'appel LLM - utilise ConsensusOrchestrator.
    """
    
    def __init__(self):
        self._config = load_consensus_config()
        self._arbiters = self._config.arbiters
        
        # Cache des modèles utilisables
        self._models_cache: Dict[str, Any] = {}
    
    def get_available_models(self) -> List[Tuple[str, str]]:
        """
        Retourne les modèles configurés dans les settings PRISM.
        
        Returns:
            Liste de tuples (provider, model)
        """
        models = []
        for arbiter in self._arbiters:
            models.append((arbiter.provider, arbiter.model))
        return models
    
    async def call_model(
        self,
        provider: str,
        model: str,
        prompt: str,
        role: str = "analyst",
        timeout_ms: int = 90000,  # Increased to 90s for complex analyses
    ) -> str:
        """
        Appelle un modèle LLM via l'infrastructure existante.
        
        Args:
            provider: Provider (openrouter, anthropic, etc.)
            model: Nom du modèle
            prompt: Prompt à envoyer
            role: Rôle de l'agent (pour logging)
            timeout_ms: Timeout en ms
            
        Returns:
            Réponse du modèle
        """
        from python.helpers.print_style import PrintStyle
        from python.helpers import llm_provider
        
        arbiter_name = f"{provider}/{model}"
        PrintStyle(font_color="cyan").print(
            f"🔍 AdversarialLLMCaller: calling {arbiter_name} as {role}..."
        )
        
        try:
            # Utiliser le provider existant
            if not llm_provider.is_provider_available():
                # Mode simulation
                PrintStyle(font_color="yellow").print(
                    f"⚠️ LLM provider unavailable, using simulation"
                )
                return self._simulate_response(role, prompt)
            
            wrapper = llm_provider.get_provider(provider, model)
            
            response = await asyncio.wait_for(
                wrapper.generate(
                    prompt=prompt,
                    temperature=0.1,  # Quasi-déterministe pour reproductibilité
                    max_tokens=1500,
                ),
                timeout=timeout_ms / 1000,
            )
            
            PrintStyle(font_color="green").print(
                f"✅ Got response from {arbiter_name}: {len(response)} chars"
            )
            
            return response
            
        except asyncio.TimeoutError:
            PrintStyle(font_color="red").print(
                f"⏱️ TIMEOUT for {arbiter_name} after {timeout_ms}ms"
            )
            raise
        except Exception as e:
            PrintStyle(font_color="red").print(
                f"❌ ERROR calling {arbiter_name}: {e}"
            )
            raise
    
    def _simulate_response(self, role: str, prompt: str) -> str:
        """Simule une réponse pour les tests."""
        return json.dumps({
            "main_conclusions": [
                f"[SIMULATED] Analyse {role} de la question",
                f"[SIMULATED] Points clés identifiés"
            ],
            "key_arguments": [f"[SIMULATED] Argument principal {role}"],
            "sources": [{"type": "simulated", "reference": f"Ref-{role}"}],
            "caveats": ["Ceci est une réponse simulée"],
            "confidence_level": "medium"
        })


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATEUR ADVERSARIAL INTÉGRÉ
# ═══════════════════════════════════════════════════════════════════════════════

class IntegratedAdversarialPipeline:
    """
    Pipeline d'instruction contradictoire intégré avec PRISM Consensus.
    
    Utilise:
    - CriticalityRouter pour la détection de domaine
    - ConsensusOrchestrator pour les votes finaux
    - Settings PRISM pour la configuration des modèles
    """
    
    def __init__(self):
        # Composants existants
        self._router = get_criticality_router()
        self._consensus = get_consensus_orchestrator()
        self._config = load_consensus_config()
        
        # Composants adversarial (sans duplication de la logique LLM)
        self._entry_gate = EntryGate()
        self._llm_caller = AdversarialLLMCaller()
        self._trace_manager = TraceabilityManager()
        self._human_interface = HumanDecisionInterface()
        
        # Dossiers actifs
        self._dossiers: Dict[str, InstructionDossier] = {}
        
        logger.info("🔄 IntegratedAdversarialPipeline initialized with PRISM arbiters")
    
    async def analyze(
        self,
        query: str,
        context: Dict[str, Any] = None,
        agent_profile: str = None,
        force_consensus: bool = False,
    ) -> InstructionDossier:
        """
        Lance une analyse contradictoire complète.
        
        Args:
            query: Question ou demande à analyser
            context: Contexte additionnel
            agent_profile: Profil d'agent (pour CriticalityRouter)
            force_consensus: Force le consensus même si non requis
            
        Returns:
            InstructionDossier avec résultats complets
        """
        context = context or {}
        start_time = time.time()
        
        # Créer le dossier
        dossier = InstructionDossier(
            id=str(uuid.uuid4()),
            query=query,
            created_at=start_time,
        )
        self._dossiers[dossier.id] = dossier
        
        from python.helpers.print_style import PrintStyle
        PrintStyle(font_color="magenta", bold=True).print(
            f"📋 Starting adversarial analysis: {dossier.id[:8]}..."
        )
        
        try:
            # ═══════════════════════════════════════════════════════════════
            # PHASE 1: QUALIFICATION VIA CRITICALITY ROUTER
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 1
            dossier.log_event(1, "qualification_started", {})
            
            # Utiliser le router existant pour déterminer le domaine
            router_assessment = self._router.assess(
                query=query,
                agent_profile=agent_profile,
            )
            
            # Mapper vers le système adversarial
            critical_domain = router_assessment.domain
            dossier.domain = DOMAIN_MAPPING.get(critical_domain, Domain.GENERAL)
            
            # Utiliser la gate d'entrée pour la criticité et le protocole
            gate_result = self._entry_gate.qualify(query, {
                "domain": dossier.domain.value,
                **context
            })
            dossier.criticality = gate_result["criticality"]
            dossier.protocol = gate_result["protocol"]
            
            # Vérifier si consensus requis via router existant
            assessment = assess_criticality(
                query=query,
                agent_profile=agent_profile,
            )
            consensus_required = assessment.requires_consensus or force_consensus
            
            dossier.log_event(1, "qualification_completed", {
                "domain": dossier.domain.value,
                "criticality": dossier.criticality.value,
                "protocol": dossier.protocol.value,
                "consensus_required": consensus_required,
            })
            
            PrintStyle(font_color="cyan").print(
                f"  Phase 1: Domain={dossier.domain.value}, "
                f"Criticality={dossier.criticality.value}, "
                f"Protocol={dossier.protocol.value}"
            )
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 2: COLLECTE MULTI-PERSPECTIVES
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 2
            dossier.log_event(2, "collection_started", {})
            
            # Déterminer les agents à utiliser selon le protocole
            agents_to_use = self._get_agents_for_protocol(dossier.protocol)
            available_models = self._llm_caller.get_available_models()
            
            PrintStyle(font_color="cyan").print(
                f"  Phase 2: Deploying {len(agents_to_use)} agents with {len(available_models)} models"
            )
            
            # Lancer les analyses en parallèle
            analyses = await self._run_parallel_analyses(
                query, dossier.domain, agents_to_use, available_models, context
            )
            dossier.agent_analyses = analyses
            
            dossier.log_event(2, "collection_completed", {
                "analyses_count": len(analyses),
            })
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 3: DÉBAT STRUCTURÉ (SI PROTOCOLE >= STANDARD)
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 3
            debate_rounds = self._get_debate_rounds(dossier.protocol)
            
            if debate_rounds > 0:
                dossier.log_event(3, "debate_started", {"rounds": debate_rounds})
                
                PrintStyle(font_color="cyan").print(
                    f"  Phase 3: Running {debate_rounds} debate rounds"
                )
                
                reviews = await self._run_debate(analyses, debate_rounds, available_models)
                dossier.peer_reviews = reviews
                
                dossier.log_event(3, "debate_completed", {
                    "reviews_count": len(reviews),
                })
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 4: AUDIT (SI PROTOCOLE >= REINFORCED)
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 4
            audit_required = dossier.protocol in [ProtocolType.REINFORCED, ProtocolType.MAXIMAL]
            
            if audit_required:
                dossier.log_event(4, "audit_started", {})
                
                PrintStyle(font_color="cyan").print(
                    f"  Phase 4: Running hallucination audit"
                )
                
                audit = await self._run_audit(analyses, dossier.peer_reviews, available_models)
                dossier.audit_report = audit
                
                dossier.log_event(4, "audit_completed", {
                    "issues_count": len(audit.issues_found),
                    "reliability": audit.overall_reliability_score,
                })
            else:
                # Audit minimal
                dossier.audit_report = AuditReport(
                    auditor_id="minimal",
                    timestamp=time.time(),
                    overall_reliability_score=0.5,
                )
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 5: CONSOLIDATION
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 5
            dossier.log_event(5, "consolidation_started", {})
            
            PrintStyle(font_color="cyan").print(
                f"  Phase 5: Consolidating results"
            )
            
            consolidation = await self._consolidate(
                analyses, dossier.peer_reviews, dossier.audit_report, available_models
            )
            
            dossier.consolidated_blocks = consolidation.get("blocks", {})
            dossier.missing_information = consolidation.get("missing_info", [])
            dossier.hypotheses_taken = consolidation.get("hypotheses", [])
            dossier.disagreement_points = consolidation.get("disagreements", [])
            
            dossier.log_event(5, "consolidation_completed", {})
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 6: CONSENSUS PRISM (SI REQUIS)
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 6
            
            if consensus_required:
                dossier.log_event(6, "prism_consensus_started", {})
                
                PrintStyle(font_color="yellow", bold=True).print(
                    f"  Phase 6: Seeking PRISM Consensus..."
                )
                
                # Utiliser le ConsensusOrchestrator existant pour le vote final
                decision_type = DOMAIN_TO_DECISION_TYPE.get(
                    dossier.domain, DecisionType.CRITICAL
                )
                
                consensus_result = await self._consensus.seek_consensus(
                    action=f"Valider l'analyse contradictoire: {query[:100]}...",
                    context={
                        "dossier_id": dossier.id,
                        "domain": dossier.domain.value,
                        "consolidated_conclusions": [
                            b.content for blocks in dossier.consolidated_blocks.values()
                            for b in blocks[:2]
                        ],
                        "reliability_score": dossier.audit_report.overall_reliability_score,
                        "disagreements": dossier.disagreement_points[:3],
                    },
                    decision_type=decision_type,
                    correlation_id=dossier.id,
                )
                
                # Stocker le résultat du consensus
                dossier.log_event(6, "prism_consensus_completed", {
                    "approved": consensus_result.approved,
                    "status": consensus_result.status.value,
                    "vote_count": consensus_result.vote_count.__dict__,
                })
                
                PrintStyle(font_color="green" if consensus_result.approved else "red").print(
                    f"  PRISM Consensus: {consensus_result.status.value}"
                )
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 7: TRAÇABILITÉ
            # ═══════════════════════════════════════════════════════════════
            dossier.current_phase = 7
            self._trace_manager.generate_trace(dossier)
            
            dossier.status = "awaiting_human_decision"
            dossier.log_event(7, "ready_for_decision", {})
            
            elapsed = time.time() - start_time
            PrintStyle(font_color="green", bold=True).print(
                f"✅ Analysis complete in {elapsed:.2f}s - {dossier.id[:8]}"
            )
            
            return dossier
            
        except Exception as e:
            dossier.status = "error"
            dossier.error = str(e)
            dossier.log_event(dossier.current_phase, "error", {"error": str(e)})
            logger.error(f"Pipeline error: {e}")
            raise
    
    def _get_agents_for_protocol(self, protocol: ProtocolType) -> List[AgentRole]:
        """Retourne les agents à utiliser selon le protocole."""
        mapping = {
            ProtocolType.LIGHT: [AgentRole.DOCTRINAL, AgentRole.PROCEDURAL],
            ProtocolType.STANDARD: [AgentRole.DOCTRINAL, AgentRole.JURISPRUDENCE, AgentRole.PROCEDURAL],
            ProtocolType.REINFORCED: [AgentRole.DOCTRINAL, AgentRole.JURISPRUDENCE, 
                                      AgentRole.PROCEDURAL, AgentRole.CONTEXTUAL],
            ProtocolType.MAXIMAL: [AgentRole.DOCTRINAL, AgentRole.JURISPRUDENCE, 
                                   AgentRole.PROCEDURAL, AgentRole.CONTEXTUAL, AgentRole.COMPARATIVE],
        }
        return mapping.get(protocol, [AgentRole.DOCTRINAL, AgentRole.PROCEDURAL])
    
    def _get_debate_rounds(self, protocol: ProtocolType) -> int:
        """Retourne le nombre de rounds de débat selon le protocole."""
        mapping = {
            ProtocolType.LIGHT: 0,
            ProtocolType.STANDARD: 1,
            ProtocolType.REINFORCED: 2,
            ProtocolType.MAXIMAL: 3,
        }
        return mapping.get(protocol, 1)
    
    async def _run_parallel_analyses(
        self,
        query: str,
        domain: Domain,
        agents: List[AgentRole],
        models: List[Tuple[str, str]],
        context: Dict[str, Any],
    ) -> Dict[str, AgentAnalysis]:
        """Lance les analyses en parallèle."""
        import re
        
        analyses = {}
        tasks = []
        
        # Assigner un modèle à chaque agent (round-robin)
        for i, role in enumerate(agents):
            provider, model = models[i % len(models)]
            
            prompt = self._build_analysis_prompt(query, domain, role, context)
            
            tasks.append(self._run_single_analysis(
                role, provider, model, prompt
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            role = agents[i]
            if isinstance(result, Exception):
                logger.error(f"Analysis failed for {role.value}: {result}")
                # Créer une analyse minimale
                result = AgentAnalysis(
                    agent_id=f"{role.value}_error",
                    agent_role=role,
                    model_used="error",
                    timestamp=time.time(),
                    main_conclusions=[f"Error: {str(result)[:100]}"],
                    caveats=["Analysis failed"],
                )
            analyses[result.agent_id] = result
        
        return analyses
    
    async def _run_single_analysis(
        self,
        role: AgentRole,
        provider: str,
        model: str,
        prompt: str,
    ) -> AgentAnalysis:
        """Exécute une analyse avec un modèle."""
        import re
        
        agent_id = f"{role.value}_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        try:
            response = await self._llm_caller.call_model(
                provider=provider,
                model=model,
                prompt=prompt,
                role=role.value,
            )
            
            # Parser la réponse JSON
            parsed = self._parse_json_response(response)
            
            return AgentAnalysis(
                agent_id=agent_id,
                agent_role=role,
                model_used=f"{provider}/{model}",
                timestamp=time.time(),
                main_conclusions=parsed.get("main_conclusions", []),
                key_arguments=parsed.get("key_arguments", []),
                risks_identified=parsed.get("risks", []),
                caveats=parsed.get("caveats", []),
                processing_time_ms=int((time.time() - start_time) * 1000),
                raw_response=response[:1000],
            )
            
        except Exception as e:
            return AgentAnalysis(
                agent_id=agent_id,
                agent_role=role,
                model_used=f"{provider}/{model}",
                timestamp=time.time(),
                main_conclusions=[f"Error: {str(e)[:100]}"],
                caveats=["Analysis failed due to error"],
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _build_analysis_prompt(
        self,
        query: str,
        domain: Domain,
        role: AgentRole,
        context: Dict[str, Any],
    ) -> str:
        """Construit le prompt pour un agent."""
        base_prompt = AGENT_ROLE_PROMPTS.get(role, "Analyse la question et réponds en JSON.")
        
        return f"""{base_prompt}

═══════════════════════════════════════════════════════════════════
DOMAINE: {domain.value.upper()}
═══════════════════════════════════════════════════════════════════

QUESTION À ANALYSER:
{query}

CONTEXTE:
{json.dumps(context, indent=2, ensure_ascii=False) if context else "Aucun contexte additionnel."}

═══════════════════════════════════════════════════════════════════
IMPORTANT
═══════════════════════════════════════════════════════════════════
- Travaille de manière INDÉPENDANTE
- Reste dans TON RÔLE SPÉCIFIQUE ({role.value})
- Sois HONNÊTE sur tes incertitudes
- Réponds UNIQUEMENT en JSON valide
"""
    
    async def _run_debate(
        self,
        analyses: Dict[str, AgentAnalysis],
        rounds: int,
        models: List[Tuple[str, str]],
    ) -> List[PeerReview]:
        """Exécute les rounds de débat."""
        reviews = []
        
        for round_num in range(rounds):
            agents = list(analyses.values())
            
            for i, reviewer in enumerate(agents):
                for j, reviewed in enumerate(agents):
                    if i != j:
                        # Utiliser un modèle différent pour la revue
                        provider, model = models[(i + j) % len(models)]
                        
                        review = await self._conduct_review(
                            reviewer, reviewed, analyses, provider, model
                        )
                        reviews.append(review)
        
        return reviews
    
    async def _conduct_review(
        self,
        reviewer: AgentAnalysis,
        reviewed: AgentAnalysis,
        all_analyses: Dict[str, AgentAnalysis],
        provider: str,
        model: str,
    ) -> PeerReview:
        """Conduit une revue par les pairs."""
        prompt = f"""Tu es chargé de réviser l'analyse suivante.

ANALYSE À RÉVISER (par {reviewed.agent_role.value}):
{json.dumps({
    "conclusions": reviewed.main_conclusions,
    "arguments": reviewed.key_arguments,
    "caveats": reviewed.caveats,
}, indent=2, ensure_ascii=False)}

Identifie:
1. Les points faibles
2. Les contradictions
3. Les zones incertaines
4. Les corrections à proposer

Réponds en JSON:
{{
    "weaknesses": [...],
    "contradictions": [...],
    "uncertain_zones": [...],
    "corrections": [...],
    "agreement_points": [...],
    "confidence": 0.0-1.0
}}"""
        
        try:
            response = await self._llm_caller.call_model(
                provider, model, prompt, f"reviewer_{reviewer.agent_role.value}"
            )
            parsed = self._parse_json_response(response)
            
            return PeerReview(
                reviewer_id=reviewer.agent_id,
                reviewed_agent_id=reviewed.agent_id,
                timestamp=time.time(),
                weaknesses=parsed.get("weaknesses", []),
                uncertain_zones=parsed.get("uncertain_zones", []),
                corrections_proposed=parsed.get("corrections", []),
                agreement_points=parsed.get("agreement_points", []),
                confidence_in_review=parsed.get("confidence", 0.5),
            )
        except Exception as e:
            return PeerReview(
                reviewer_id=reviewer.agent_id,
                reviewed_agent_id=reviewed.agent_id,
                timestamp=time.time(),
                weaknesses=[f"Review error: {str(e)[:50]}"],
            )
    
    async def _run_audit(
        self,
        analyses: Dict[str, AgentAnalysis],
        reviews: List[PeerReview],
        models: List[Tuple[str, str]],
    ) -> AuditReport:
        """Exécute l'audit des hallucinations."""
        provider, model = models[0]  # Utiliser le premier modèle
        
        # Agréger le contenu à auditer
        content = {
            "analyses": {
                a.agent_role.value: {
                    "conclusions": a.main_conclusions,
                    "caveats": a.caveats,
                }
                for a in analyses.values()
            },
            "debate_issues": [
                w for r in reviews for w in r.weaknesses
            ][:10],
        }
        
        prompt = f"""Tu es un auditeur interne. Ta mission est de CHASSER les hallucinations.

CONTENU À AUDITER:
{json.dumps(content, indent=2, ensure_ascii=False)}

Identifie:
1. Affirmations non sourcées
2. Raisonnements circulaires
3. Approximations
4. Interprétations présentées comme faits

Réponds en JSON:
{{
    "unsourced_claims": [...],
    "circular_reasonings": [...],
    "approximations": [...],
    "interpretations_as_facts": [...],
    "overall_reliability_score": 0.0-1.0,
    "recommendations": [...]
}}"""
        
        try:
            response = await self._llm_caller.call_model(
                provider, model, prompt, "hallucination_hunter"
            )
            parsed = self._parse_json_response(response)
            
            return AuditReport(
                auditor_id=f"auditor_{uuid.uuid4().hex[:8]}",
                timestamp=time.time(),
                unsourced_claims=parsed.get("unsourced_claims", []),
                circular_reasonings=parsed.get("circular_reasonings", []),
                approximations=parsed.get("approximations", []),
                interpretations_as_facts=parsed.get("interpretations_as_facts", []),
                overall_reliability_score=parsed.get("overall_reliability_score", 0.5),
                prudence_recommendations=parsed.get("recommendations", []),
            )
        except Exception as e:
            return AuditReport(
                auditor_id="error",
                timestamp=time.time(),
                overall_reliability_score=0.3,
                prudence_recommendations=[f"Audit failed: {str(e)[:50]}"],
            )
    
    async def _consolidate(
        self,
        analyses: Dict[str, AgentAnalysis],
        reviews: List[PeerReview],
        audit: AuditReport,
        models: List[Tuple[str, str]],
    ) -> Dict[str, Any]:
        """Consolide les résultats."""
        provider, model = models[0]
        
        content = {
            "conclusions": [
                c for a in analyses.values() for c in a.main_conclusions
            ],
            "caveats": [
                c for a in analyses.values() for c in a.caveats
            ],
            "audit_score": audit.overall_reliability_score,
            "debate_issues": len([w for r in reviews for w in r.weaknesses]),
        }
        
        prompt = f"""Consolide les analyses suivantes en classant chaque élément par niveau de fiabilité.

MATÉRIAU:
{json.dumps(content, indent=2, ensure_ascii=False)}

Classe chaque conclusion dans:
- highly_reliable: consensus fort + pas d'issues
- probable: majorité d'accord
- uncertain: débat ou issues
- disputed: contradictions non résolues

Réponds en JSON:
{{
    "highly_reliable": [...],
    "probable": [...],
    "uncertain": [...],
    "disputed": [...],
    "missing_info": [...],
    "hypotheses": [...],
    "disagreements": [...]
}}"""
        
        try:
            response = await self._llm_caller.call_model(
                provider, model, prompt, "synthesizer"
            )
            parsed = self._parse_json_response(response)
            
            # Construire les blocs
            blocks = {}
            for level in [ConfidenceLevel.HIGHLY_RELIABLE, ConfidenceLevel.PROBABLE,
                         ConfidenceLevel.UNCERTAIN, ConfidenceLevel.DISPUTED]:
                items = parsed.get(level.value, [])
                if items:
                    blocks[level] = [
                        ConsolidatedBlock(
                            id=f"block_{uuid.uuid4().hex[:8]}",
                            category=level,
                            content=item if isinstance(item, str) else str(item),
                        )
                        for item in items
                    ]
            
            return {
                "blocks": blocks,
                "missing_info": parsed.get("missing_info", []),
                "hypotheses": parsed.get("hypotheses", []),
                "disagreements": parsed.get("disagreements", []),
            }
        except Exception as e:
            return {
                "blocks": {},
                "missing_info": [f"Consolidation error: {str(e)[:50]}"],
                "hypotheses": [],
                "disagreements": [],
            }
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse une réponse structurée (texte ou JSON).
        
        Extrait les informations clés du format texte structuré français.
        """
        import re
        
        if not response:
            return {}
        
        result = {}
        cleaned = response.strip()
        
        # Essayer JSON d'abord (au cas où)
        try:
            # Retirer markdown
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```\w*\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Parser le format texte structuré français
        conclusions = []
        caveats = []
        sources = []
        
        # Patterns pour extraire les sections
        section_patterns = {
            "conclusions": [
                r"CONCLUSIONS?\s*PRINCIPALES?\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"JURISPRUDENCE\s*APPLICABLE\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"ANALYSE\s*PROCÉDURALE\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"PARTIES?\s*EN\s*PRÉSENCE\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"APPROCHE\s*COMPARATIVE\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
            ],
            "sources": [
                r"FONDEMENTS?\s*JURIDIQUES?\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"ÉVOLUTIONS?\s*RÉCENTES?\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
            ],
            "caveats": [
                r"POINTS?\s*D['']ATTENTION\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"RISQUES?\s*IDENTIFIÉS?\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
                r"ÉLÉMENTS?\s*MANQUANTS?\s*:?\s*([\s\S]*?)(?=\n[A-Z]{2,}|\n---|\Z)",
            ],
        }
        
        for category, patterns in section_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, cleaned, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Extraire les bullet points
                    bullets = re.findall(r'[•\-\*]\s*(.+?)(?=\n[•\-\*]|\n\n|\Z)', match, re.DOTALL)
                    if bullets:
                        items = [b.strip() for b in bullets if b.strip() and len(b.strip()) > 10]
                        if category == "conclusions":
                            conclusions.extend(items)
                        elif category == "sources":
                            sources.extend(items)
                        elif category == "caveats":
                            caveats.extend(items)
        
        # Fallback: extraire les lignes significatives
        if not conclusions:
            lines = cleaned.split('\n')
            for line in lines:
                line = line.strip()
                # Ignorer les titres et lignes courtes
                if line and len(line) > 30 and not line.isupper() and not line.startswith('#'):
                    # Nettoyer les bullets
                    line = re.sub(r'^[•\-\*]\s*', '', line)
                    if line:
                        conclusions.append(line)
        
        # Construire le résultat
        if conclusions:
            result["main_conclusions"] = conclusions[:8]
        if sources:
            result["sources"] = [{"reference": s} for s in sources[:5]]
        if caveats:
            result["caveats"] = caveats[:5]
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERFACE PUBLIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_dossier(self, dossier_id: str) -> Optional[InstructionDossier]:
        """Récupère un dossier."""
        return self._dossiers.get(dossier_id)
    
    def get_trace_markdown(self, dossier_id: str) -> str:
        """Récupère la trace en Markdown."""
        dossier = self._dossiers.get(dossier_id)
        if not dossier:
            raise ValueError(f"Dossier {dossier_id} not found")
        trace = self._trace_manager.trace_store.get(dossier_id)
        if not trace:
            trace = self._trace_manager.generate_trace(dossier)
        return self._trace_manager.export_trace_markdown(trace)
    
    def get_decision_presentation(self, dossier_id: str) -> Dict[str, Any]:
        """Prépare la présentation pour décision humaine."""
        dossier = self._dossiers.get(dossier_id)
        if not dossier:
            raise ValueError(f"Dossier {dossier_id} not found")
        return self._human_interface.present_for_decision(dossier)
    
    def record_decision(
        self,
        dossier_id: str,
        decision: str,
        acknowledged_risks: List[str],
        notes: str = "",
    ) -> bool:
        """Enregistre la décision humaine."""
        return self._human_interface.record_human_decision(
            dossier_id, decision, acknowledged_risks, notes
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_pipeline_instance: Optional[IntegratedAdversarialPipeline] = None


def get_adversarial_pipeline() -> IntegratedAdversarialPipeline:
    """Retourne l'instance singleton du pipeline intégré."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = IntegratedAdversarialPipeline()
    return _pipeline_instance


async def analyze_with_adversarial(
    query: str,
    context: Dict[str, Any] = None,
    agent_profile: str = None,
) -> InstructionDossier:
    """
    Fonction raccourci pour lancer une analyse adversariale.
    
    Usage:
        from python.helpers.adversarial_consensus_integration import analyze_with_adversarial
        
        dossier = await analyze_with_adversarial(
            "Mon client risque la prison pour fraude fiscale...",
            agent_profile="legal_safe"
        )
    """
    pipeline = get_adversarial_pipeline()
    return await pipeline.analyze(query, context, agent_profile)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "IntegratedAdversarialPipeline",
    "AdversarialLLMCaller",
    "get_adversarial_pipeline",
    "analyze_with_adversarial",
    "DOMAIN_MAPPING",
    "DOMAIN_TO_DECISION_TYPE",
]

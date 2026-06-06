"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚠️ DÉPRÉCIÉ (ADR-010, réalignement chemin critique — 30 mai 2026).          ║
║  Façade redondante au-dessus de `ConsensusOrchestrator.seek_consensus`.      ║
║  Aucun appelant production sur le chemin critique actif (seul l'agent        ║
║  médical l'importe de façon optionnelle). À MIGRER vers l'API canonique      ║
║  `run_consensus`/`seek_consensus` puis SUPPRIMER (cf.                        ║
║  docs/audit/critical_path_remediation_report.md, P1).                        ║
║  NE PAS construire de nouveau chemin sur ce module.                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║            RESEARCH CONSENSUS INTEGRATION — Zero Hallucination               ║
║                                                                              ║
║  Intégration complète du consensus PRISM dans le flux de recherche.          ║
║                                                                              ║
║  Pipeline:                                                                   ║
║  1. Détection de criticité (CriticalityRouter)                               ║
║  2. Collecte de données (MCPs via ResearchExecutor)                          ║
║  3. Construction du pack de preuves (EvidencePack)                           ║
║  4. Synthèse avec draft de claims                                            ║
║  5. VALIDATION CONSENSUS OBLIGATOIRE si domaine critique                     ║
║  6. Génération finale ou FAIL-CLOSED                                         ║
║                                                                              ║
║  "Pas de source = pas de claim"                                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalityAssessment,
    CriticalDomain,
    DecisionTypeForDomain,
    get_criticality_router,
    CONSENSUS_REQUIRED_PROFILES,
)

from python.helpers.evidence import (
    EvidencePack,
    EvidenceBuilder,
    Source,
    Claim,
    SourceType,
    SourceReliability,
    ClaimStatus,
    EvidenceValidationResult,
    DOMAIN_EVIDENCE_REQUIREMENTS,
    validate_evidence_for_consensus,
)
from python.helpers.consensus_contracts import (
    ResponseEnvelopeSchema,
    ConsensusSummarySchema,
    ReliabilityTierSchema,
    ReliabilityTierEnum,
    ConsensusStatusEnum,
)

from python.helpers.consensus_arbiter import (
    ConsensusOrchestrator,
    ConsensusResult,
    seek_consensus,
    get_consensus_orchestrator,
    SimulationError,
)

from python.helpers.consensus_manager import DecisionType, ConsensusStatus

logger = logging.getLogger("research_consensus")


# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchConsensusConfig:
    """Configuration du pipeline de recherche avec consensus."""
    
    # Evidence
    strict_evidence_mode: bool = True  # TRUE par défaut pour domaines critiques
    min_sources_override: Optional[int] = None
    
    # Consensus
    consensus_enabled: bool = True
    consensus_timeout_ms: int = 10000
    
    # Comportement
    fail_closed: bool = True  # Toujours fail-closed
    allow_partial_evidence: bool = False  # Ne pas autoriser preuves partielles
    
    # Logging
    audit_all_decisions: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchConclusion:
    """Conclusion de recherche validée par consensus."""
    
    # Identifiants
    correlation_id: str
    query: str
    
    # Résultat
    success: bool
    approved: bool
    conclusion_text: str
    response_envelope: Optional[ResponseEnvelopeSchema] = None
    
    # Preuves
    evidence_pack: Optional[EvidencePack] = None
    evidence_valid: bool = False
    
    # Consensus
    consensus_result: Optional[ConsensusResult] = None
    consensus_required: bool = False
    
    # Criticité
    assessment: Optional[CriticalityAssessment] = None
    
    # Métriques
    total_duration_ms: int = 0
    data_collection_ms: int = 0
    consensus_ms: int = 0
    
    # Audit
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Génère un dict pour l'audit complet."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": self.query[:500],
            "success": self.success,
            "approved": self.approved,
            "consensus_required": self.consensus_required,
            "consensus_status": self.consensus_result.status.value if self.consensus_result else None,
            "evidence_valid": self.evidence_valid,
            "domain": self.assessment.domain.value if self.assessment else None,
            "strict_evidence_mode": self.assessment.strict_evidence_mode if self.assessment else False,
            "total_duration_ms": self.total_duration_ms,
            "data_collection_ms": self.data_collection_ms,
            "consensus_ms": self.consensus_ms,
            "sources_count": len(self.evidence_pack.sources) if self.evidence_pack else 0,
            "claims_count": len(self.evidence_pack.claims) if self.evidence_pack else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH CONSENSUS PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchConsensusPipeline:
    """
    Pipeline de recherche avec consensus obligatoire pour domaines critiques.
    
    Usage:
        pipeline = ResearchConsensusPipeline()
        
        result = await pipeline.research(
            query="What are the legal requirements for GDPR compliance?",
            agent_profile="legal_safe",
        )
        
        if result.approved:
            # Conclusion validée
            print(result.conclusion_text)
        else:
            # Fail-closed
            print(result.conclusion_text)  # Message d'erreur
    """
    
    def __init__(
        self,
        config: ResearchConsensusConfig = None,
        criticality_router: CriticalityRouter = None,
        consensus_orchestrator: ConsensusOrchestrator = None,
    ):
        self.config = config or ResearchConsensusConfig()
        self.router = criticality_router or get_criticality_router()
        self.orchestrator = consensus_orchestrator or get_consensus_orchestrator()
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
        
        logger.info("ResearchConsensusPipeline initialized")
    
    async def research(
        self,
        query: str,
        agent_profile: str = "",
        research_results: List[Dict[str, Any]] = None,
        correlation_id: str = None,
        force_consensus: bool = None,
    ) -> ResearchConclusion:
        """
        Exécute une recherche avec validation par consensus si nécessaire.
        
        Args:
            query: Requête de recherche
            agent_profile: Profil de l'agent (legal_safe, researcher, etc.)
            research_results: Résultats de recherche pré-collectés (optionnel)
            correlation_id: ID de corrélation
            force_consensus: Forcer le consensus (overrides assessment)
            
        Returns:
            ResearchConclusion avec le résultat validé ou fail-closed
        """
        start_time = time.time()
        correlation_id = correlation_id or str(uuid.uuid4())
        audit_trail = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 1: Évaluation de criticité
        # ═══════════════════════════════════════════════════════════════════════
        
        assessment = self.router.assess(
            query=query,
            agent_profile=agent_profile,
            force_consensus=force_consensus,
        )
        
        audit_trail.append({
            "step": "criticality_assessment",
            "timestamp": time.time(),
            "result": assessment.to_dict(),
        })
        
        logger.info(
            f"Criticality assessment: domain={assessment.domain.value}, "
            f"requires_consensus={assessment.requires_consensus} "
            f"[{correlation_id}]"
        )
        
        # Déterminer le mode strict evidence
        strict_mode = (
            self.config.strict_evidence_mode and 
            assessment.strict_evidence_mode
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 2: Construction du pack de preuves
        # ═══════════════════════════════════════════════════════════════════════
        
        evidence_start = time.time()
        
        evidence_builder = EvidenceBuilder(
            query=query,
            domain=assessment.domain,
            strict_mode=strict_mode,
        )
        
        # Si des résultats pré-collectés sont fournis, les ajouter
        if research_results:
            for result in research_results:
                tool_name = result.get("tool_name", "unknown")
                evidence_builder.add_mcp_result(tool_name, result)
        
        evidence_pack = evidence_builder.build()
        evidence_valid = evidence_pack.validation_result == EvidenceValidationResult.SUFFICIENT
        
        data_collection_ms = int((time.time() - evidence_start) * 1000)
        
        audit_trail.append({
            "step": "evidence_collection",
            "timestamp": time.time(),
            "sources_count": len(evidence_pack.sources),
            "validation_result": evidence_pack.validation_result.value,
            "evidence_valid": evidence_valid,
        })
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 3: Vérifier si preuves suffisantes (fail-soft)
        # ═══════════════════════════════════════════════════════════════════════
        
        if strict_mode and not evidence_valid:
            total_duration_ms = int((time.time() - start_time) * 1000)
            answer = (
                "Evidence is insufficient to provide a high-confidence answer. "
                "Below is a cautious response with explicit unknowns and next steps."
            )
            envelope = ResponseEnvelopeSchema(
                answer=answer,
                reliability_tiers=[
                    ReliabilityTierSchema(
                        tier=ReliabilityTierEnum.LOW,
                        claims=[],
                        rationale="Insufficient evidence for strict mode.",
                        sources=[],
                    )
                ],
                unknowns=[evidence_pack.get_missing_evidence_message()],
                recommended_next_steps=[
                    "Collect additional primary sources",
                    "Clarify the question and constraints",
                    "Consult a domain expert if decisions are time-critical",
                ],
                consensus=ConsensusSummarySchema(
                    status=ConsensusStatusEnum.SKIPPED,
                    quorum="2/3",
                    votes_summary={
                        "approvals": 0,
                        "rejections": 0,
                        "abstentions": 0,
                        "unavailable": 0,
                        "total": 0,
                    },
                    warnings=["insufficient_evidence"],
                ),
                debug_trace={"correlation_id": correlation_id},
            )
            
            conclusion = ResearchConclusion(
                correlation_id=correlation_id,
                query=query,
                success=True,
                approved=False,
                conclusion_text=answer,
                response_envelope=envelope,
                evidence_pack=evidence_pack,
                evidence_valid=False,
                consensus_result=None,
                consensus_required=assessment.requires_consensus,
                assessment=assessment,
                total_duration_ms=total_duration_ms,
                data_collection_ms=data_collection_ms,
                audit_trail=audit_trail,
            )
            
            self._log_conclusion(conclusion)
            return conclusion
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 4: Génération de la conclusion draft
        # ═══════════════════════════════════════════════════════════════════════
        
        draft_conclusion = await self._generate_draft_conclusion(
            query, evidence_pack, assessment
        )
        
        audit_trail.append({
            "step": "draft_generation",
            "timestamp": time.time(),
            "draft_length": len(draft_conclusion),
        })
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 5: Validation par consensus (si requis)
        # ═══════════════════════════════════════════════════════════════════════
        
        consensus_result = None
        approved = True
        consensus_ms = 0
        
        if assessment.requires_consensus and self.config.consensus_enabled:
            consensus_start = time.time()
            
            try:
                consensus_result = await self.orchestrator.seek_consensus(
                    action=f"Validate research conclusion for domain: {assessment.domain.value}",
                    context={
                        "query": query[:1000],
                        "agent_profile": agent_profile,
                        "domain": assessment.domain.value,
                        "conclusion_draft": draft_conclusion[:3000],
                        "sources_count": len(evidence_pack.sources),
                        "evidence_valid": evidence_valid,
                    },
                    decision_type=self._map_decision_type(assessment.decision_type),
                    evidence_pack=evidence_pack.to_audit_dict(),
                    correlation_id=correlation_id,
                )
                
                approved = consensus_result.approved
                consensus_ms = int((time.time() - consensus_start) * 1000)
                
                audit_trail.append({
                    "step": "consensus_validation",
                    "timestamp": time.time(),
                    "approved": approved,
                    "status": consensus_result.status.value,
                    "votes": consensus_result.vote_count.__dict__,
                    "decision_time_ms": consensus_result.decision_time_ms,
                })
                
            except Exception as e:
                logger.error(f"Consensus failed: {e}")
                approved = False
                audit_trail.append({
                    "step": "consensus_error",
                    "timestamp": time.time(),
                    "error": str(e)[:200],
                })
        
        # ═══════════════════════════════════════════════════════════════════════
        # ÉTAPE 6: Finalisation
        # ═══════════════════════════════════════════════════════════════════════
        
        if approved:
            final_conclusion = self._format_approved_conclusion(
                draft_conclusion, evidence_pack, consensus_result
            )
            success = True
        else:
            final_conclusion = (
                "Consensus was not reached. The response below is a cautious draft "
                "with low reliability and explicit unknowns.\n\n"
                + draft_conclusion
            )
            success = True
        
        total_duration_ms = int((time.time() - start_time) * 1000)
        
        # Build a fail-soft envelope for critical paths
        response_envelope = None
        if assessment.requires_consensus:
            summary_status = (
                consensus_result.status
                if consensus_result
                else ConsensusStatusEnum.INFRA_FAILURE
            )
            votes_summary = (
                consensus_result.vote_count.__dict__
                if consensus_result
                else {
                    "approvals": 0,
                    "rejections": 0,
                    "abstentions": 0,
                    "unavailable": 0,
                    "total": 0,
                }
            )
            tier = ReliabilityTierEnum.HIGH if approved else ReliabilityTierEnum.LOW
            response_envelope = ResponseEnvelopeSchema(
                answer=final_conclusion,
                reliability_tiers=[
                    ReliabilityTierSchema(
                        tier=tier,
                        claims=[],
                        rationale=(
                            "Consensus-approved output."
                            if approved else
                            "Consensus not reached; output is low reliability."
                        ),
                        sources=[s.url for s in evidence_pack.sources if getattr(s, "url", None)],
                    )
                ],
                unknowns=[] if approved else ["Consensus not reached"],
                recommended_next_steps=(
                    [] if approved else [
                        "Provide more specific context and sources",
                        "Collect primary references",
                        "Consult a domain expert for final decisions",
                    ]
                ),
                consensus=ConsensusSummarySchema(
                    status=summary_status,
                    quorum="2/3",
                    votes_summary=votes_summary,
                    warnings=[] if approved else ["consensus_not_reached"],
                ),
                debug_trace={"correlation_id": correlation_id},
            )
            
            logger.info(json.dumps({
                "event": "envelope_emit",
                "correlation_id": correlation_id,
                "status": summary_status.value,
                "tier": tier.value,
            }))

        conclusion = ResearchConclusion(
            correlation_id=correlation_id,
            query=query,
            success=success,
            approved=approved,
            conclusion_text=final_conclusion,
            response_envelope=response_envelope,
            evidence_pack=evidence_pack,
            evidence_valid=evidence_valid,
            consensus_result=consensus_result,
            consensus_required=assessment.requires_consensus,
            assessment=assessment,
            total_duration_ms=total_duration_ms,
            data_collection_ms=data_collection_ms,
            consensus_ms=consensus_ms,
            audit_trail=audit_trail,
        )
        
        self._log_conclusion(conclusion)
        
        return conclusion
    
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _generate_draft_conclusion(
        self,
        query: str,
        evidence_pack: EvidencePack,
        assessment: CriticalityAssessment,
    ) -> str:
        """
        Génère un brouillon de conclusion basé sur les preuves.
        
        Dans une implémentation complète, ceci appellerait un LLM
        pour synthétiser les sources. Pour l'instant, on génère
        un template structuré.
        """
        sources_summary = []
        for source in evidence_pack.sources.values():
            sources_summary.append(
                f"- [{source.title}]({source.url or 'N/A'}) "
                f"({source.source_type.value}, {source.reliability.value})"
            )
        
        sources_text = "\n".join(sources_summary) if sources_summary else "Aucune source collectée."
        
        return f"""## Synthèse de recherche

**Requête**: {query}
**Domaine**: {assessment.domain.value}
**Sources analysées**: {len(evidence_pack.sources)}

### Sources

{sources_text}

### Analyse

Cette conclusion est basée sur {len(evidence_pack.sources)} source(s) validée(s).
Le niveau de confiance dépend de la fiabilité des sources citées.

---
*Cette conclusion a été générée automatiquement et doit être validée par consensus.*
"""
    
    def _format_approved_conclusion(
        self,
        draft: str,
        evidence_pack: EvidencePack,
        consensus_result: Optional[ConsensusResult],
    ) -> str:
        """Formate la conclusion approuvée avec badge de validation."""
        badge = "\n\n---\n✅ **Conclusion Validée**"
        
        if consensus_result:
            badge += (
                f"\n- Consensus: {consensus_result.status.value}"
                f"\n- Votes: {consensus_result.vote_count.approvals}/"
                f"{consensus_result.vote_count.total}"
                f"\n- Temps de décision: {consensus_result.decision_time_ms}ms"
            )
        
        badge += f"\n- Sources vérifiées: {len(evidence_pack.sources)}"
        badge += f"\n- Validation des preuves: {evidence_pack.validation_result.value}"
        
        return draft + badge
    
    def _format_rejected_conclusion(
        self,
        query: str,
        assessment: CriticalityAssessment,
        consensus_result: Optional[ConsensusResult],
        correlation_id: str,
    ) -> str:
        """Formate la réponse en cas de rejet du consensus."""
        votes_info = ""
        if consensus_result:
            votes_info = (
                f"- Approvals: {consensus_result.vote_count.approvals}\n"
                f"- Rejections: {consensus_result.vote_count.rejections}\n"
                f"- Abstentions: {consensus_result.vote_count.abstentions}"
            )
        
        return f"""## ⚠️ Consensus non obtenu — Réponse prudente

**Domaine critique**: {assessment.domain.value}
**Mode strict evidence**: {'Oui' if assessment.strict_evidence_mode else 'Non'}
**Statut**: {'REJECTED' if consensus_result else 'ERROR'}

### Détail des votes

{votes_info or "Aucune information de vote disponible."}

### Ce que cela signifie

La conclusion proposée n'a pas obtenu le consensus requis des arbitres indépendants.
Par principe de précaution (fail-closed), aucune affirmation n'est faite.

### Recommandations

1. **Fournir plus de contexte** pour permettre une analyse plus précise
2. **Rechercher des sources additionnelles** pour étayer les claims
3. **Consulter un expert humain** pour ce type de question critique
4. **Reformuler la question** de manière plus précise

### Traçabilité

- Correlation ID: `{correlation_id}`
- Domaine: {assessment.domain.value}
- Raisons de criticité: {', '.join(assessment.reasons[:3])}

*Ce système applique le principe "fail-closed": en cas de doute, aucune affirmation non validée n'est transmise.*
"""
    
    def _map_decision_type(
        self,
        domain_type: DecisionTypeForDomain,
    ) -> DecisionType:
        """Map le type de décision du router vers celui du consensus."""
        mapping = {
            DecisionTypeForDomain.LEGAL_DECISION: DecisionType.CRITICAL,
            DecisionTypeForDomain.MEDICAL_DECISION: DecisionType.CRITICAL,
            DecisionTypeForDomain.SCIENTIFIC_VALIDATION: DecisionType.RESEARCH_VALIDATION,
            DecisionTypeForDomain.FINANCIAL_DECISION: DecisionType.CRITICAL,
            DecisionTypeForDomain.SECURITY_DECISION: DecisionType.SECURITY,
            DecisionTypeForDomain.RESEARCH_VALIDATION: DecisionType.RESEARCH_VALIDATION,
            DecisionTypeForDomain.CRITICAL: DecisionType.CRITICAL,
        }
        return mapping.get(domain_type, DecisionType.CRITICAL)
    
    def _log_conclusion(self, conclusion: ResearchConclusion):
        """Log la conclusion pour audit."""
        audit_entry = conclusion.to_audit_dict()
        self._audit_log.append(audit_entry)
        
        status = "✅ APPROVED" if conclusion.approved else "❌ REJECTED"
        logger.info(
            f"{status} Research conclusion: "
            f"domain={conclusion.assessment.domain.value if conclusion.assessment else 'N/A'}, "
            f"sources={len(conclusion.evidence_pack.sources) if conclusion.evidence_pack else 0}, "
            f"duration={conclusion.total_duration_ms}ms "
            f"[{conclusion.correlation_id}]"
        )
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Retourne le log d'audit complet."""
        return self._audit_log.copy()


# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_pipeline_instance: Optional[ResearchConsensusPipeline] = None


def get_research_consensus_pipeline() -> ResearchConsensusPipeline:
    """Retourne l'instance singleton du pipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = ResearchConsensusPipeline()
    return _pipeline_instance


async def research_with_consensus(
    query: str,
    agent_profile: str = "",
    research_results: List[Dict[str, Any]] = None,
    correlation_id: str = None,
    force_consensus: bool = None,
) -> ResearchConclusion:
    """
    Fonction raccourci pour lancer une recherche avec consensus.
    
    Usage:
        from python.helpers.research_consensus_integration import research_with_consensus
        
        result = await research_with_consensus(
            query="What are the GDPR requirements?",
            agent_profile="legal_safe",
        )
        
        if result.approved:
            print(result.conclusion_text)
    """
    pipeline = get_research_consensus_pipeline()
    return await pipeline.research(
        query, agent_profile, research_results, correlation_id, force_consensus
    )


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Config
    "ResearchConsensusConfig",
    # Data
    "ResearchConclusion",
    # Classes
    "ResearchConsensusPipeline",
    # Functions
    "get_research_consensus_pipeline",
    "research_with_consensus",
]

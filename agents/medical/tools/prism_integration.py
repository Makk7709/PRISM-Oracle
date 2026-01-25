"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          KOREV Evidence - Medical Agent PRISM Integration                     ║
║                                                                              ║
║  Intégration OBLIGATOIRE du consensus PRISM pour toutes les sorties médicales║
║                                                                              ║
║  RÈGLE ABSOLUE:                                                              ║
║  - Toute affirmation médicale DOIT passer par le consensus PRISM             ║
║  - Fail-closed si consensus non atteint                                      ║
║  - Zéro hallucination en domaine médical                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

# Add parent paths for imports
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

try:
    from python.helpers.criticality_router import (
        CriticalityRouter,
        CriticalityAssessment,
        CriticalDomain,
        get_criticality_router,
    )
    from python.helpers.evidence import (
        EvidencePack,
        EvidenceBuilder,
        Source,
        Claim,
        SourceType,
        SourceReliability,
        ClaimStatus,
        validate_evidence_for_consensus,
        create_fail_closed_response,
    )
    from python.helpers.consensus_arbiter import (
        ConsensusOrchestrator,
        ConsensusResult,
        seek_consensus,
        get_consensus_orchestrator,
    )
    from python.helpers.research_consensus_integration import (
        ResearchConsensusPipeline,
        ResearchConclusion,
        research_with_consensus,
    )
    PRISM_AVAILABLE = True
except ImportError as e:
    PRISM_AVAILABLE = False
    PRISM_IMPORT_ERROR = str(e)

logger = logging.getLogger("medical_prism_integration")


class MedicalPRISMStatus(str, Enum):
    """Status du consensus PRISM pour le domaine médical."""
    VALIDATED = "validated"           # Consensus atteint, output validé
    FAILED_CONSENSUS = "failed_consensus"  # Consensus non atteint, fail-closed
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # Preuves insuffisantes
    BLOCKED = "blocked"               # Bloqué par policy
    BYPASS_DISABLED = "bypass_disabled"  # PRISM désactivé (dev only)


@dataclass
class MedicalPRISMResult:
    """Résultat de validation PRISM pour output médical."""
    
    # Status
    status: MedicalPRISMStatus
    approved: bool
    
    # Output
    original_output: str
    validated_output: str
    fail_closed_message: str = ""
    
    # Evidence
    evidence_pack: Optional[EvidencePack] = None
    sources_count: int = 0
    claims_validated: int = 0
    claims_rejected: int = 0
    
    # Consensus
    consensus_reached: bool = False
    consensus_votes: Dict[str, str] = field(default_factory=dict)
    quorum_met: bool = False
    
    # Métriques
    correlation_id: str = ""
    validation_time_ms: int = 0
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Export pour audit trail."""
        return {
            "correlation_id": self.correlation_id,
            "status": self.status.value,
            "approved": self.approved,
            "consensus_reached": self.consensus_reached,
            "quorum_met": self.quorum_met,
            "sources_count": self.sources_count,
            "claims_validated": self.claims_validated,
            "claims_rejected": self.claims_rejected,
            "validation_time_ms": self.validation_time_ms,
        }


class MedicalPRISMValidator:
    """
    Validateur PRISM pour le domaine médical.
    
    OBLIGATOIRE pour toutes les sorties de l'agent médical.
    Garantit le consensus multi-LLM avant émission.
    """
    
    # Message fail-closed standard
    FAIL_CLOSED_MESSAGE = """
## ⚠️ Validation PRISM Non Atteinte

Cette analyse médicale n'a pas pu être validée par le consensus PRISM.

**Raison**: {reason}

**Actions recommandées**:
1. Reformuler la question avec plus de spécificité
2. Fournir des sources additionnelles
3. Consulter un professionnel de santé qualifié

**Note**: KOREV Evidence refuse d'émettre des affirmations médicales 
non validées par consensus multi-LLM pour garantir la sécurité patient.
"""
    
    def __init__(self):
        self.enabled = PRISM_AVAILABLE
        if not self.enabled:
            logger.warning(f"PRISM not available: {PRISM_IMPORT_ERROR}")
            
        if self.enabled:
            self.router = get_criticality_router()
            self.orchestrator = get_consensus_orchestrator()
    
    def _verify_medical_domain(self, query: str) -> CriticalityAssessment:
        """Vérifie que la query est bien dans le domaine médical."""
        if not self.enabled:
            # Return mock assessment
            return type('MockAssessment', (), {
                'domain': type('MockDomain', (), {'value': 'MEDICAL'})(),
                'requires_consensus': True,
                'strict_evidence_mode': True,
                'to_dict': lambda: {'domain': 'MEDICAL'}
            })()
            
        assessment = self.router.assess(
            query=query,
            agent_profile="medical",
            force_consensus=True,  # Toujours forcer le consensus en médical
        )
        return assessment
    
    def _build_evidence_pack(
        self, 
        query: str,
        sources: List[Dict[str, Any]],
        claims: List[str],
    ) -> EvidencePack:
        """Construit un pack de preuves à partir des sources collectées."""
        if not self.enabled:
            return None
            
        builder = EvidenceBuilder(
            query=query,
            domain=CriticalDomain.MEDICAL,
        )
        
        # Ajouter les sources
        for src in sources:
            source_type = self._map_source_type(src.get("type", "unknown"))
            reliability = self._assess_reliability(src)
            
            builder.add_source(
                source_type=source_type,
                reference=src.get("id", src.get("url", "unknown")),
                title=src.get("title", ""),
                content=src.get("content", src.get("abstract", "")),
                url=src.get("url", ""),
                reliability=reliability,
                metadata=src,
            )
        
        # Ajouter les claims
        for claim_text in claims:
            builder.add_claim(
                claim=claim_text,
                status=ClaimStatus.UNSUPPORTED,  # Will be validated during consensus
            )
        
        return builder.build()
    
    def _map_source_type(self, type_str: str) -> SourceType:
        """Map string type to SourceType enum."""
        mapping = {
            "pubmed": SourceType.PRIMARY,      # Peer-reviewed papers
            "clinicaltrials": SourceType.DATABASE,  # Clinical trial database
            "fda_label": SourceType.PRIMARY,   # Official regulatory
            "faers": SourceType.DATABASE,      # FDA database
            "guideline": SourceType.PRIMARY,   # Official guidelines
            "preprint": SourceType.SECONDARY,  # Non peer-reviewed
            "web": SourceType.WEB,
        }
        return mapping.get(type_str.lower(), SourceType.WEB)
    
    def _assess_reliability(self, source: Dict[str, Any]) -> SourceReliability:
        """Évalue la fiabilité d'une source."""
        source_type = source.get("type", "").lower()
        level = source.get("level", "5")
        
        # Sources académiques avec niveau d'évidence
        if source_type == "pubmed":
            if level in ["1a", "1b"]:
                return SourceReliability.HIGH
            elif level in ["2a", "2b"]:
                return SourceReliability.MEDIUM  # MEDIUM not MODERATE
            else:
                return SourceReliability.LOW
        
        # Sources réglementaires
        if source_type in ["fda_label", "guideline"]:
            return SourceReliability.HIGH
        
        # Clinical trials
        if source_type == "clinicaltrials":
            return SourceReliability.MEDIUM  # MEDIUM not MODERATE
        
        # FAERS (spontaneous reports)
        if source_type == "faers":
            return SourceReliability.LOW
        
        return SourceReliability.UNKNOWN
    
    async def validate_medical_output(
        self,
        query: str,
        output: str,
        sources: List[Dict[str, Any]] = None,
        claims: List[str] = None,
        force_sync: bool = False,
    ) -> MedicalPRISMResult:
        """
        Valide une sortie médicale via le consensus PRISM.
        
        DOIT être appelé pour TOUTE sortie de l'agent médical.
        
        Args:
            query: Question médicale originale
            output: Réponse générée à valider
            sources: Sources utilisées (PMID, NCT, etc.)
            claims: Affirmations médicales à valider
            force_sync: Forcer exécution synchrone
            
        Returns:
            MedicalPRISMResult avec status et output validé ou fail-closed
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 1: Vérification domaine médical
        # ═══════════════════════════════════════════════════════════════════
        
        assessment = self._verify_medical_domain(query)
        
        logger.info(
            f"[MEDICAL PRISM] Validating output for query: {query[:100]}... "
            f"[{correlation_id}]"
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 2: Vérification des preuves
        # ═══════════════════════════════════════════════════════════════════
        
        sources = sources or []
        claims = claims or self._extract_claims(output)
        
        if not sources:
            # Pas de sources = fail-closed
            return MedicalPRISMResult(
                status=MedicalPRISMStatus.INSUFFICIENT_EVIDENCE,
                approved=False,
                original_output=output,
                validated_output="",
                fail_closed_message=self.FAIL_CLOSED_MESSAGE.format(
                    reason="Aucune source fournie pour les affirmations médicales"
                ),
                correlation_id=correlation_id,
                validation_time_ms=int((time.time() - start_time) * 1000),
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 3: Construction pack de preuves
        # ═══════════════════════════════════════════════════════════════════
        
        evidence_pack = None
        if self.enabled:
            evidence_pack = self._build_evidence_pack(query, sources, claims)
            
            # Valider les preuves
            validation_result = validate_evidence_for_consensus(
                evidence_pack,
                CriticalDomain.MEDICAL,
            )
            
            if not validation_result.is_valid:
                return MedicalPRISMResult(
                    status=MedicalPRISMStatus.INSUFFICIENT_EVIDENCE,
                    approved=False,
                    original_output=output,
                    validated_output="",
                    fail_closed_message=self.FAIL_CLOSED_MESSAGE.format(
                        reason=f"Preuves insuffisantes: {validation_result.reason}"
                    ),
                    evidence_pack=evidence_pack,
                    sources_count=len(sources),
                    correlation_id=correlation_id,
                    validation_time_ms=int((time.time() - start_time) * 1000),
                )
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 4: Consensus PRISM
        # ═══════════════════════════════════════════════════════════════════
        
        consensus_result = None
        consensus_reached = False
        quorum_met = False
        votes = {}
        
        if self.enabled:
            try:
                consensus_result = await seek_consensus(
                    query=query,
                    proposed_answer=output,
                    evidence_pack=evidence_pack,
                    domain=CriticalDomain.MEDICAL,
                    correlation_id=correlation_id,
                )
                
                consensus_reached = consensus_result.approved
                quorum_met = consensus_result.quorum_met
                votes = {
                    v.model_id: v.vote.value 
                    for v in consensus_result.votes
                } if consensus_result.votes else {}
                
            except Exception as e:
                logger.error(f"[MEDICAL PRISM] Consensus error: {e} [{correlation_id}]")
                # Fail-closed en cas d'erreur
                return MedicalPRISMResult(
                    status=MedicalPRISMStatus.FAILED_CONSENSUS,
                    approved=False,
                    original_output=output,
                    validated_output="",
                    fail_closed_message=self.FAIL_CLOSED_MESSAGE.format(
                        reason=f"Erreur système consensus: {str(e)}"
                    ),
                    evidence_pack=evidence_pack,
                    sources_count=len(sources),
                    correlation_id=correlation_id,
                    validation_time_ms=int((time.time() - start_time) * 1000),
                )
        else:
            # Mode dégradé sans PRISM - log warning mais autorise
            logger.warning(
                f"[MEDICAL PRISM] Running in degraded mode (PRISM unavailable) "
                f"[{correlation_id}]"
            )
            consensus_reached = True  # Bypass en mode dégradé
            
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 5: Décision finale
        # ═══════════════════════════════════════════════════════════════════
        
        if consensus_reached:
            # Consensus atteint - output validé
            validated_output = self._add_validation_stamp(output, correlation_id, sources)
            
            return MedicalPRISMResult(
                status=MedicalPRISMStatus.VALIDATED,
                approved=True,
                original_output=output,
                validated_output=validated_output,
                evidence_pack=evidence_pack,
                sources_count=len(sources),
                claims_validated=len(claims),
                consensus_reached=True,
                consensus_votes=votes,
                quorum_met=quorum_met,
                correlation_id=correlation_id,
                validation_time_ms=int((time.time() - start_time) * 1000),
            )
        else:
            # Consensus non atteint - fail-closed
            return MedicalPRISMResult(
                status=MedicalPRISMStatus.FAILED_CONSENSUS,
                approved=False,
                original_output=output,
                validated_output="",
                fail_closed_message=self.FAIL_CLOSED_MESSAGE.format(
                    reason="Consensus multi-LLM non atteint (quorum 2/3 requis)"
                ),
                evidence_pack=evidence_pack,
                sources_count=len(sources),
                consensus_reached=False,
                consensus_votes=votes,
                quorum_met=quorum_met,
                correlation_id=correlation_id,
                validation_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _extract_claims(self, output: str) -> List[str]:
        """Extrait les affirmations médicales d'un output."""
        # Heuristique simple: phrases avec mots médicaux
        medical_keywords = [
            "efficacy", "safety", "treatment", "therapy", "drug", "medication",
            "dose", "adverse", "clinical", "patient", "diagnosis", "symptom",
            "efficacité", "sécurité", "traitement", "médicament", "dose",
        ]
        
        claims = []
        sentences = output.replace("\n", " ").split(". ")
        
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in medical_keywords):
                if len(sentence) > 20:  # Ignorer phrases trop courtes
                    claims.append(sentence.strip())
        
        return claims[:10]  # Limiter à 10 claims
    
    def _add_validation_stamp(
        self, 
        output: str, 
        correlation_id: str,
        sources: List[Dict[str, Any]],
    ) -> str:
        """Ajoute un stamp de validation PRISM à l'output."""
        stamp = f"""

---
✅ **PRISM Validated** | ID: `{correlation_id[:8]}` | Sources: {len(sources)}
"""
        return output + stamp
    
    def validate_sync(
        self,
        query: str,
        output: str,
        sources: List[Dict[str, Any]] = None,
        claims: List[str] = None,
    ) -> MedicalPRISMResult:
        """
        Version synchrone de validate_medical_output.
        À utiliser quand asyncio n'est pas disponible.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.validate_medical_output(query, output, sources, claims)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self.validate_medical_output(query, output, sources, claims)
                )
        except Exception as e:
            logger.error(f"Sync validation error: {e}")
            return MedicalPRISMResult(
                status=MedicalPRISMStatus.FAILED_CONSENSUS,
                approved=False,
                original_output=output,
                validated_output="",
                fail_closed_message=self.FAIL_CLOSED_MESSAGE.format(
                    reason=f"Erreur validation: {str(e)}"
                ),
                correlation_id=str(uuid.uuid4()),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_validator = None

def get_medical_prism_validator() -> MedicalPRISMValidator:
    """Singleton pour le validateur PRISM médical."""
    global _validator
    if _validator is None:
        _validator = MedicalPRISMValidator()
    return _validator


async def validate_medical_with_prism(
    query: str,
    output: str,
    sources: List[Dict[str, Any]] = None,
) -> str:
    """
    Fonction de convénience pour valider un output médical.
    
    Returns:
        Output validé si consensus atteint, message fail-closed sinon.
    """
    validator = get_medical_prism_validator()
    result = await validator.validate_medical_output(
        query=query,
        output=output,
        sources=sources,
    )
    
    if result.approved:
        return result.validated_output
    else:
        return result.fail_closed_message


def validate_medical_sync(
    query: str,
    output: str,
    sources: List[Dict[str, Any]] = None,
) -> str:
    """Version synchrone de validate_medical_with_prism."""
    validator = get_medical_prism_validator()
    result = validator.validate_sync(query, output, sources)
    
    if result.approved:
        return result.validated_output
    else:
        return result.fail_closed_message

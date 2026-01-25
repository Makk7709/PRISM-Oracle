"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CRITICAL DECISION GATE                                     ║
║                                                                              ║
║  Point de contrôle UNIQUE et INÉVITABLE pour toutes les décisions critiques. ║
║                                                                              ║
║  RÈGLES ABSOLUES:                                                            ║
║  1. AUCUNE réponse critique ne peut sortir sans passer par ce gate           ║
║  2. Domaine critique détecté → strict evidence + consensus OBLIGATOIRE       ║
║  3. Zéro claim sans source en domaine critique                               ║
║  4. Fail-closed si preuves insuffisantes                                     ║
║                                                                              ║
║  Ce module est le SEUL endroit où la règle "consensus requis" est décidée.   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import os
import re
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
    CONSENSUS_REQUIRED_PROFILES,
    get_criticality_router,
)

from python.helpers.evidence import (
    EvidencePack,
    EvidenceBuilder,
    Source,
    Claim,
    ClaimStatus,
    EvidenceValidationResult,
    validate_evidence_for_consensus,
    create_fail_closed_response,
)

# Medical contract validation (T9 claim-first enforcement)
try:
    from python.helpers.medical_contract import (
        validate_medical_output,
        MedicalDecision,
        MedicalValidationResult,
        detect_red_flags,
    )
    MEDICAL_CONTRACT_AVAILABLE = True
except ImportError:
    MEDICAL_CONTRACT_AVAILABLE = False

logger = logging.getLogger("critical_decision_gate")


# ═══════════════════════════════════════════════════════════════════════════════
# GATE RESULT
# ═══════════════════════════════════════════════════════════════════════════════

class GateDecision(str, Enum):
    """Décision du gate."""
    ALLOW = "allow"           # Réponse autorisée
    REQUIRE_CONSENSUS = "require_consensus"  # Consensus requis
    FAIL_CLOSED = "fail_closed"  # Refusé (preuves insuffisantes)
    BLOCKED = "blocked"       # Bloqué (policy violation)


@dataclass
class GateResult:
    """Résultat complet du passage par le gate."""
    
    # Décision
    decision: GateDecision
    can_emit: bool
    
    # Assessment original
    assessment: CriticalityAssessment
    
    # Evidence
    evidence_pack: Optional[EvidencePack] = None
    evidence_valid: bool = False
    
    # Consensus
    consensus_required: bool = False
    consensus_result: Optional[Dict[str, Any]] = None
    
    # Output
    original_output: str = ""
    validated_output: str = ""
    fail_closed_response: str = ""
    
    # Métriques
    gate_time_ms: int = 0
    correlation_id: str = ""
    
    # Flags pour logs
    override_applied: bool = False
    override_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Export pour audit."""
        return {
            "decision": self.decision.value,
            "can_emit": self.can_emit,
            "domain": self.assessment.domain.value,
            "requires_consensus": self.consensus_required,
            "evidence_valid": self.evidence_valid,
            "gate_time_ms": self.gate_time_ms,
            "correlation_id": self.correlation_id,
            "override_applied": self.override_applied,
            "override_reason": self.override_reason,
            "strict_evidence_mode": self.assessment.strict_evidence_mode,
        }
    
    def to_log_entry(self) -> Dict[str, Any]:
        """
        Entry pour structured logging.
        
        IMPORTANT: Schema versionné pour stabilité des tests.
        Si tu changes ce schema, incrémente log_schema_version.
        """
        return {
            # Schema version — incrémente si tu changes les champs
            "log_schema_version": "1.0.0",
            
            # Champs stables
            "event": "gate_decision",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gate_applied": True,  # TOUJOURS True si ce log existe
            "domain": self.assessment.domain.value,
            "requires_consensus": self.consensus_required,
            "strict_evidence_mode": self.assessment.strict_evidence_mode,
            "decision": self.decision.value,
            "can_emit": self.can_emit,
            "correlation_id": self.correlation_id,
            "override_applied": self.override_applied,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLAIM EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns qui indiquent un claim factuel/assertif
CLAIM_PATTERNS = [
    # Affirmations directes
    r"\b(is|are|was|were|will be|has been|have been)\s+\w+",
    r"\b(est|sont|était|étaient|sera|seront|a été|ont été)\s+\w+",
    
    # Conclusions
    r"\b(therefore|thus|hence|consequently|as a result)\b",
    r"\b(donc|ainsi|par conséquent|en conséquence)\b",
    
    # Recommandations
    r"\b(should|must|recommend|advise|suggest)\b",
    r"\b(devrait|doit|recommande|conseille|suggère)\b",
    
    # Affirmations médicales
    r"\b(diagnos|treat|prescri|symptom|condition|disease)\b",
    r"\b(diagnostic|traitement|prescrip|symptôme|maladie)\b",
    
    # Affirmations légales
    r"\b(legal|illegal|lawful|unlawful|compliant|liable)\b",
    r"\b(légal|illégal|conforme|responsable|licite|illicite)\b",
    
    # Affirmations financières
    r"\b(invest|profit|loss|return|risk|portfolio)\b",
    r"\b(investir|profit|perte|rendement|risque)\b",
]


def extract_claims_from_text(
    text: str,
    domain: CriticalDomain,
) -> List[str]:
    """
    Extrait les claims factuels d'un texte.
    
    Pour les domaines critiques, chaque claim devra être sourcé.
    """
    claims = []
    
    # Splitter en phrases
    sentences = re.split(r'[.!?]\s+', text)
    
    # Filtrer les phrases qui contiennent des patterns de claim
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        
        # Vérifier si la phrase contient un pattern de claim
        is_claim = False
        for pattern in CLAIM_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                is_claim = True
                break
        
        if is_claim:
            claims.append(sentence)
    
    return claims


def assert_no_unsourced_claims(
    answer: str,
    evidence_pack: Optional[EvidencePack],
    domain: CriticalDomain,
) -> Tuple[bool, List[str]]:
    """
    Vérifie qu'aucun claim critique n'est fait sans source.
    
    INVARIANT: En domaine critique, chaque claim doit avoir supported_by_source_ids non vide.
    
    Args:
        answer: Réponse à vérifier
        evidence_pack: Pack de preuves
        domain: Domaine de la réponse
        
    Returns:
        (all_sourced, unsourced_claims)
    """
    # Domaines non critiques → OK
    if domain in [CriticalDomain.DEFAULT, CriticalDomain.COMPLIANCE]:
        return True, []
    
    # Pas d'evidence pack → tous les claims sont non sourcés
    if not evidence_pack or not evidence_pack.sources:
        claims = extract_claims_from_text(answer, domain)
        return len(claims) == 0, claims
    
    # Vérifier chaque claim dans l'evidence pack
    unsourced = []
    for claim in evidence_pack.claims:
        if claim.status == ClaimStatus.UNSUPPORTED:
            unsourced.append(claim.text)
        elif not claim.supported_by_source_ids:
            unsourced.append(claim.text)
    
    return len(unsourced) == 0, unsourced


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL DECISION GATE
# ═══════════════════════════════════════════════════════════════════════════════

class CriticalDecisionGate:
    """
    Gardien central pour toutes les décisions critiques.
    
    UN SEUL ENDROIT où la règle "consensus requis" est décidée.
    
    Usage:
        gate = CriticalDecisionGate()
        
        # À l'entrée
        result = gate.enforce_or_route(query, agent_profile)
        if result.consensus_required:
            # Activer pipeline gouverné
        
        # À la sortie
        result = await gate.validate_final_output(output, agent_profile, evidence_pack)
        if not result.can_emit:
            # Retourner fail_closed_response
    """
    
    def __init__(self):
        self.router = get_criticality_router()
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
        self._decisions_count = 0
        
        logger.info("🚧 CriticalDecisionGate initialized")
    
    # ─────────────────────────────────────────────────────────────────────────
    # ENTRY POINT: enforce_or_route
    # ─────────────────────────────────────────────────────────────────────────
    
    def enforce_or_route(
        self,
        query: str,
        agent_profile: str = "",
        action: str = "",
        context_metadata: Optional[Dict[str, Any]] = None,
        force_consensus: Optional[bool] = None,
    ) -> GateResult:
        """
        Point d'entrée: décide du pipeline à utiliser.
        
        Appelé au début du traitement d'une requête.
        
        Args:
            query: Requête utilisateur
            agent_profile: Profil de l'agent actif
            action: Action demandée (optionnel)
            context_metadata: Métadonnées additionnelles
            force_consensus: Forcer le consensus (override)
            
        Returns:
            GateResult avec la décision
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        # Évaluer la criticité
        assessment = self.router.assess(
            query=query,
            agent_profile=agent_profile,
            task_metadata=context_metadata,
            force_consensus=force_consensus,
        )
        
        # Détecter override
        override_applied = False
        override_reason = ""
        
        # RÈGLE: si le caller dit force_consensus=False mais le domain est critique → OVERRIDE
        if force_consensus is False and assessment.requires_consensus:
            override_applied = True
            override_reason = (
                f"Consensus forced despite force_consensus=False "
                f"(domain={assessment.domain.value}, profile={agent_profile})"
            )
            logger.warning(f"⚠️ OVERRIDE: {override_reason}")
        
        # Construire le résultat
        gate_time_ms = int((time.time() - start_time) * 1000)
        
        result = GateResult(
            decision=GateDecision.REQUIRE_CONSENSUS if assessment.requires_consensus else GateDecision.ALLOW,
            can_emit=not assessment.requires_consensus,  # Si consensus requis, pas encore émissible
            assessment=assessment,
            consensus_required=assessment.requires_consensus,
            gate_time_ms=gate_time_ms,
            correlation_id=correlation_id,
            override_applied=override_applied,
            override_reason=override_reason,
        )
        
        # Log
        self._log_decision(result, "enforce_or_route")
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────────
    # EXIT POINT: validate_final_output
    # ─────────────────────────────────────────────────────────────────────────
    
    async def validate_final_output(
        self,
        output: str,
        agent_profile: str = "",
        evidence_pack: Optional[EvidencePack] = None,
        context_metadata: Optional[Dict[str, Any]] = None,
        consensus_result: Optional[Dict[str, Any]] = None,
        correlation_id: str = None,
    ) -> GateResult:
        """
        Point de sortie: valide avant émission finale.
        
        Vérifie:
        1. Domaine critique → consensus doit avoir été obtenu
        2. Strict evidence → tous les claims doivent être sourcés
        3. Pas de claim non sourcé en domaine critique
        
        Args:
            output: Texte de sortie à valider
            agent_profile: Profil de l'agent
            evidence_pack: Pack de preuves
            context_metadata: Métadonnées
            consensus_result: Résultat du consensus (si obtenu)
            correlation_id: ID de corrélation
            
        Returns:
            GateResult avec can_emit=True/False
        """
        start_time = time.time()
        correlation_id = correlation_id or str(uuid.uuid4())
        
        # Évaluer la criticité du contenu de sortie
        assessment = self.router.assess(
            query=output[:1000],  # Limiter pour perf
            agent_profile=agent_profile,
            task_metadata=context_metadata,
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 1: Consensus requis → consensus obtenu ?
        # ═══════════════════════════════════════════════════════════════════════
        
        if assessment.requires_consensus:
            if not consensus_result or not consensus_result.get("approved"):
                # Consensus requis mais pas obtenu → fail-closed
                fail_response = self._create_fail_closed_no_consensus(
                    output, assessment, correlation_id
                )
                
                result = GateResult(
                    decision=GateDecision.FAIL_CLOSED,
                    can_emit=False,
                    assessment=assessment,
                    consensus_required=True,
                    original_output=output,
                    fail_closed_response=fail_response,
                    gate_time_ms=int((time.time() - start_time) * 1000),
                    correlation_id=correlation_id,
                )
                
                self._log_decision(result, "validate_final_output")
                return result
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 2: Strict evidence → preuves suffisantes ?
        # ═══════════════════════════════════════════════════════════════════════
        
        evidence_valid = True
        if assessment.strict_evidence_mode:
            if evidence_pack:
                evidence_valid = evidence_pack.validation_result == EvidenceValidationResult.SUFFICIENT
            else:
                evidence_valid = False
            
            if not evidence_valid:
                fail_response = create_fail_closed_response(
                    query=output[:200],
                    domain=assessment.domain,
                    evidence_pack=evidence_pack,
                )
                
                result = GateResult(
                    decision=GateDecision.FAIL_CLOSED,
                    can_emit=False,
                    assessment=assessment,
                    evidence_pack=evidence_pack,
                    evidence_valid=False,
                    consensus_required=assessment.requires_consensus,
                    original_output=output,
                    fail_closed_response=fail_response,
                    gate_time_ms=int((time.time() - start_time) * 1000),
                    correlation_id=correlation_id,
                )
                
                self._log_decision(result, "validate_final_output")
                return result
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 3: Zéro claim non sourcé
        # ═══════════════════════════════════════════════════════════════════════
        
        if assessment.domain in [CriticalDomain.LEGAL, CriticalDomain.MEDICAL, CriticalDomain.SCIENTIFIC]:
            all_sourced, unsourced_claims = assert_no_unsourced_claims(
                output, evidence_pack, assessment.domain
            )
            
            if not all_sourced and unsourced_claims:
                # En mode strict, on refuse
                if assessment.strict_evidence_mode:
                    fail_response = self._create_fail_closed_unsourced(
                        output, assessment, unsourced_claims, correlation_id
                    )
                    
                    result = GateResult(
                        decision=GateDecision.FAIL_CLOSED,
                        can_emit=False,
                        assessment=assessment,
                        evidence_pack=evidence_pack,
                        evidence_valid=False,
                        consensus_required=assessment.requires_consensus,
                        original_output=output,
                        fail_closed_response=fail_response,
                        gate_time_ms=int((time.time() - start_time) * 1000),
                        correlation_id=correlation_id,
                    )
                    
                    self._log_decision(result, "validate_final_output")
                    return result
                else:
                    # Mode non-strict: warning mais on laisse passer
                    logger.warning(
                        f"Unsourced claims detected in non-strict mode: "
                        f"{len(unsourced_claims)} claims [{correlation_id}]"
                    )
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 4: MEDICAL DOMAIN → StructuredResponse Contract (T9)
        # ═══════════════════════════════════════════════════════════════════════
        
        if assessment.domain == CriticalDomain.MEDICAL and MEDICAL_CONTRACT_AVAILABLE:
            # Déterminer si mode offline
            offline_mode = os.environ.get("OFFLINE_MODE", "").lower() == "true"
            
            # Tenter de parser la sortie comme JSON/dict
            output_data = output
            if isinstance(output, str):
                try:
                    import json
                    output_data = json.loads(output)
                except (json.JSONDecodeError, TypeError):
                    # Output est du texte libre - échec du contrat
                    output_data = output  # Garder comme string pour le validateur
            
            # Valider contre le contrat médical
            medical_result = validate_medical_output(output_data, offline_mode=offline_mode)
            
            if not medical_result.is_valid:
                logger.warning(
                    f"Medical contract violation: {medical_result.errors} "
                    f"[{correlation_id}]"
                )
                
                fail_response = self._create_fail_closed_medical_contract(
                    output, assessment, medical_result.errors, correlation_id
                )
                
                result = GateResult(
                    decision=GateDecision.FAIL_CLOSED,
                    can_emit=False,
                    assessment=assessment,
                    evidence_pack=evidence_pack,
                    evidence_valid=False,
                    consensus_required=assessment.requires_consensus,
                    original_output=output,
                    fail_closed_response=fail_response,
                    gate_time_ms=int((time.time() - start_time) * 1000),
                    correlation_id=correlation_id,
                )
                
                self._log_decision(result, "validate_final_output")
                return result
            
            logger.info(f"Medical contract validated [{correlation_id}]")
        
        # ═══════════════════════════════════════════════════════════════════════
        # TOUS LES CHECKS OK → AUTORISER
        # ═══════════════════════════════════════════════════════════════════════
        
        result = GateResult(
            decision=GateDecision.ALLOW,
            can_emit=True,
            assessment=assessment,
            evidence_pack=evidence_pack,
            evidence_valid=evidence_valid,
            consensus_required=assessment.requires_consensus,
            consensus_result=consensus_result,
            original_output=output,
            validated_output=output,
            gate_time_ms=int((time.time() - start_time) * 1000),
            correlation_id=correlation_id,
        )
        
        self._log_decision(result, "validate_final_output")
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _create_fail_closed_no_consensus(
        self,
        output: str,
        assessment: CriticalityAssessment,
        correlation_id: str,
    ) -> str:
        """Crée une réponse fail-closed quand consensus non obtenu."""
        return f"""## ⚠️ Réponse bloquée — Consensus non obtenu

**Domaine critique détecté**: {assessment.domain.value}
**Consensus requis**: Oui
**Statut**: Non validé

### Ce que cela signifie

Cette réponse concerne un domaine critique ({assessment.domain.value}) et nécessite 
une validation par consensus de plusieurs arbitres indépendants.

Le consensus n'a pas été obtenu, soit parce que:
- Les arbitres n'ont pas approuvé la réponse
- Le consensus a expiré (timeout)
- Une erreur s'est produite

### Recommandations

1. **Reformuler votre question** de manière plus précise
2. **Consulter un expert humain** pour ce type de question
3. **Fournir plus de contexte** si possible

### Traçabilité

- Correlation ID: `{correlation_id}`
- Domaine: {assessment.domain.value}
- Raisons: {', '.join(assessment.reasons[:3])}

*Système fail-closed: en cas de doute, aucune affirmation non validée n'est faite.*
"""
    
    def _create_fail_closed_unsourced(
        self,
        output: str,
        assessment: CriticalityAssessment,
        unsourced_claims: List[str],
        correlation_id: str,
    ) -> str:
        """Crée une réponse fail-closed pour claims non sourcés."""
        claims_text = "\n".join(f"- {c[:100]}..." for c in unsourced_claims[:5])
        
        return f"""## ⚠️ Réponse bloquée — Claims non sourcés détectés

**Domaine critique**: {assessment.domain.value}
**Mode strict evidence**: Activé
**Problème**: {len(unsourced_claims)} affirmation(s) sans source

### Affirmations non sourcées détectées

{claims_text}
{"..." if len(unsourced_claims) > 5 else ""}

### Ce que cela signifie

En domaine {assessment.domain.value}, toute affirmation factuelle doit être 
soutenue par au moins une source vérifiable.

### Recommandations

1. Rechercher des sources pour étayer ces affirmations
2. Reformuler les affirmations de manière moins assertive
3. Indiquer explicitement l'incertitude si applicable

### Traçabilité

- Correlation ID: `{correlation_id}`
- Domaine: {assessment.domain.value}
- Claims non sourcés: {len(unsourced_claims)}

*Principe "zéro hallucination": pas de source = pas d'affirmation.*
"""
    
    def _create_fail_closed_medical_contract(
        self,
        output: str,
        assessment: CriticalityAssessment,
        errors: List[str],
        correlation_id: str,
    ) -> str:
        """Crée une réponse fail-closed pour violation du contrat médical."""
        errors_text = "\n".join(f"- {e}" for e in errors[:5])
        
        return f"""## ⚠️ NON VALIDABLE — Contrat médical non respecté

**Domaine**: MEDICAL
**Validation**: ÉCHEC
**Raison**: Sortie non conforme au format StructuredResponse

### Violations détectées

{errors_text}

### Ce que cela signifie

En domaine médical, toute sortie DOIT respecter le contrat StructuredResponse :
- `claims[]` : Liste de claims avec source_ids non vides
- `citations[]` : Sources référencées par les claims
- `meta` : Métadonnées incluant evidence_grade et consensus_status
- Invariant PV : source_type="pv" => evidence_grade="VL"
- Invariant citation : claim.source_ids ⊆ citations.ids

### Recommandations

Cette sortie a été bloquée pour non-conformité au contrat.
Consulter un professionnel de santé pour obtenir des informations médicales fiables.

### Traçabilité

- Correlation ID: `{correlation_id}`
- Domaine: {assessment.domain.value}
- Erreurs: {len(errors)}

*Contrat médical T9 : aucune sortie médicale sans validation structurée.*
"""
    
    def _log_decision(self, result: GateResult, operation: str):
        """Log la décision pour audit."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            **result.to_log_entry(),
        }
        
        self._audit_log.append(entry)
        self._decisions_count += 1
        
        # Structured logging
        logger.info(
            f"Gate decision: {result.decision.value} | "
            f"domain={result.assessment.domain.value} | "
            f"consensus_required={result.consensus_required} | "
            f"can_emit={result.can_emit} | "
            f"[{result.correlation_id}]"
        )
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Retourne le log d'audit."""
        return self._audit_log.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques."""
        return {
            "total_decisions": self._decisions_count,
            "audit_log_size": len(self._audit_log),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_gate_instance: Optional[CriticalDecisionGate] = None


def get_decision_gate() -> CriticalDecisionGate:
    """Retourne l'instance singleton du gate."""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = CriticalDecisionGate()
    return _gate_instance


def enforce_or_route(
    query: str,
    agent_profile: str = "",
    action: str = "",
    context_metadata: Optional[Dict[str, Any]] = None,
    force_consensus: Optional[bool] = None,
) -> GateResult:
    """
    Fonction raccourci pour enforce_or_route.
    
    Usage:
        from python.helpers.critical_decision_gate import enforce_or_route
        
        result = enforce_or_route(query, agent_profile="legal_safe")
        if result.consensus_required:
            # ...
    """
    return get_decision_gate().enforce_or_route(
        query, agent_profile, action, context_metadata, force_consensus
    )


async def validate_final_output(
    output: str,
    agent_profile: str = "",
    evidence_pack: Optional[EvidencePack] = None,
    context_metadata: Optional[Dict[str, Any]] = None,
    consensus_result: Optional[Dict[str, Any]] = None,
    correlation_id: str = None,
) -> GateResult:
    """
    Fonction raccourci pour validate_final_output.
    
    Usage:
        from python.helpers.critical_decision_gate import validate_final_output
        
        result = await validate_final_output(output, agent_profile="legal_safe")
        if not result.can_emit:
            return result.fail_closed_response
    """
    return await get_decision_gate().validate_final_output(
        output, agent_profile, evidence_pack, context_metadata, 
        consensus_result, correlation_id
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "GateDecision",
    # Data
    "GateResult",
    # Functions
    "extract_claims_from_text",
    "assert_no_unsourced_claims",
    # Classes
    "CriticalDecisionGate",
    # Singleton
    "get_decision_gate",
    "enforce_or_route",
    "validate_final_output",
]

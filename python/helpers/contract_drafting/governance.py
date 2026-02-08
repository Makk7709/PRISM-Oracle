"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           GOVERNANCE — Règles de gouvernance juridique                      ║
║                                                                              ║
║  Constantes et fonctions de gouvernance du pipeline contractuel.            ║
║                                                                              ║
║  RÈGLES CRITIQUES:                                                           ║
║    1. Decision.type = "legal_contract" (jamais "pricing" ou autre)          ║
║    2. MULTI_AGENT_CONSENSUS ne peut JAMAIS donner un verdict juridique      ║
║    3. legal_safe a un droit de VETO ABSOLU                                  ║
║    4. Aucun APPROVED global sans PASS legal_safe                            ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.contract_drafting.models import GateVerdict


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Le type de décision pour tout pipeline contractuel.
# JAMAIS "pricing", "strategy", ou tout autre type.
DECISION_GOVERNANCE_TYPE = "legal_contract"

# Multi-agent consensus NE PEUT JAMAIS overrider le veto legal_safe.
_CONSENSUS_CAN_OVERRIDE_LEGAL_GATE = False

# legal_safe a un droit de veto ABSOLU.
_LEGAL_SAFE_VETO_ABSOLUTE = True


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def can_consensus_override_legal_gate() -> bool:
    """MULTI_AGENT_CONSENSUS peut-il overrider le veto legal_safe ?
    
    RÉPONSE: NON — JAMAIS.
    
    Le consensus multi-agent est conçu pour les décisions stratégiques,
    pas pour les verdicts juridiques. Le veto legal_safe est absolu.
    
    Returns:
        False — toujours
    """
    return _CONSENSUS_CAN_OVERRIDE_LEGAL_GATE


def is_legal_safe_veto_absolute() -> bool:
    """legal_safe a-t-il un droit de veto absolu ?
    
    RÉPONSE: OUI — TOUJOURS.
    
    Returns:
        True — toujours
    """
    return _LEGAL_SAFE_VETO_ABSOLUTE


def is_contract_globally_approved(gate_verdict: "GateVerdict") -> bool:
    """Vérifie si un contrat est globalement approuvé.
    
    INVARIANT: Un contrat est approuvé ⟺ legal_safe verdict = APPROVE
    
    Aucun autre mécanisme (consensus, override, etc.) ne peut approuver
    un contrat sans le PASS de legal_safe.
    
    Args:
        gate_verdict: Le verdict de la gate legal_safe
    
    Returns:
        True si approuvé, False sinon
    """
    from python.helpers.contract_drafting.models import GateVerdictEnum
    
    if gate_verdict.verdict != GateVerdictEnum.APPROVE:
        return False
    if not gate_verdict.can_release:
        return False
    return True


def get_decision_type() -> str:
    """Retourne le type de décision pour le pipeline contractuel.
    
    Returns:
        "legal_contract" — toujours
    """
    return DECISION_GOVERNANCE_TYPE

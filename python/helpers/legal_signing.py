"""
Mapping de signature pour le chemin pipeline legal (ADR-010 / P1-1).

Module volontairement léger (aucune dépendance LLM/pipeline) afin de rester
importable et testable de façon déterministe, indépendamment du boot des
providers de consensus.
"""

from __future__ import annotations

from typing import Optional, Tuple, Dict, Any


def map_legal_consensus(
    consensus_status: Optional[str],
    consensus_id: Optional[str],
    correlation_id: str,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Mappe `LegalOutput.consensus_status` → (consensus_result, requires_consensus).

    Doctrine ADR-010 (P1-1) — respecte la décision DU pipeline legal :
      - ``APPROVED``                          → (consensus approuvé, True)
      - ``REJECTED``/``NO_CONSENSUS``/``INFRA_FAILURE``
                                              → (consensus non approuvé, True)
                                                (émis avec bannière via policy fail-soft)
      - ``None`` / autre                      → (None, False)
                                                (consensus non exécuté : INFO/low-risk)
    """
    status = (consensus_status or "").upper()
    if status == "APPROVED":
        return ({
            "status": "APPROVED", "approved": True,
            "proposal_id": consensus_id, "correlation_id": correlation_id,
        }, True)
    if status in {"REJECTED", "NO_CONSENSUS", "INFRA_FAILURE"}:
        return ({
            "status": status, "approved": False,
            "proposal_id": consensus_id, "correlation_id": correlation_id,
        }, True)
    return (None, False)

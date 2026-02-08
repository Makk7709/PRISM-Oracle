"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           EXPORT CONTROL — Blocage PDF/DOC sans PASS juridique             ║
║                                                                              ║
║  INVARIANT: Aucun contrat ne peut être exporté (PDF, DOC, client-ready)    ║
║  tant qu'un P0 juridique subsiste.                                          ║
║                                                                              ║
║  Fonctions:                                                                  ║
║    is_export_allowed(output) → bool                                         ║
║    get_export_stamp(output) → str (mention "VALIDÉ PAR LEGAL_SAFE")        ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.contract_drafting.models import DraftingOutput


def is_export_allowed(output: "DraftingOutput") -> bool:
    """Vérifie si un contrat peut être exporté (PDF/DOC/client).
    
    INVARIANT: export autorisé ⟺ gate_passed = True ET can_release = True
    
    Args:
        output: Le résultat du pipeline de rédaction
    
    Returns:
        True si l'export est autorisé, False sinon
    """
    if not output.gate_passed:
        return False
    if not output.gate_verdict.can_release:
        return False
    if output.gate_verdict.has_p0():
        return False
    if not output.rendered_contract:
        return False
    return True


def get_export_stamp(output: "DraftingOutput") -> str:
    """Génère le stamp d'export si autorisé.
    
    Le stamp contient la mention "VALIDÉ PAR LEGAL_SAFE" et la date.
    
    Args:
        output: Le résultat du pipeline
    
    Returns:
        str — le stamp d'export, ou une mention de refus
    """
    if not is_export_allowed(output):
        return (
            "EXPORT REFUSÉ — Gate LEGAL_SAFE non PASS. "
            "Le contrat ne peut pas être exporté."
        )
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    p1_count = output.gate_verdict.p1_count()
    p1_mention = f" (avec {p1_count} avertissement(s) P1)" if p1_count > 0 else ""
    
    return (
        f"══════════════════════════════════════════════\n"
        f"  VALIDÉ PAR LEGAL_SAFE GATE — PASS{p1_mention}\n"
        f"  Date: {now}\n"
        f"  Correlation ID: {output.draft.correlation_id}\n"
        f"  PROJET — À VALIDER PAR UN JURISTE QUALIFIÉ\n"
        f"══════════════════════════════════════════════"
    )

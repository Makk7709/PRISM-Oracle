"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           EXPORT CONTROL — Blocage PDF/DOC sans PASS juridique (V2)        ║
║                                                                              ║
║  INVARIANT: Aucun contrat ne peut être exporté (PDF, DOC, client-ready)    ║
║  tant qu'un P0 juridique subsiste.                                          ║
║                                                                              ║
║  HARDENED V2:                                                                ║
║    - Template version tracking dans le stamp                                ║
║    - Audit log de chaque tentative d'export                                ║
║    - Double-check des invariants                                            ║
║                                                                              ║
║  Fonctions:                                                                  ║
║    is_export_allowed(output) → bool                                         ║
║    get_export_stamp(output) → str (mention "VALIDÉ PAR LEGAL_SAFE")        ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python.helpers.contract_drafting.models import DraftingOutput

logger = logging.getLogger("contract_drafting.export_control")


def is_export_allowed(output: "DraftingOutput") -> bool:
    """Vérifie si un contrat peut être exporté (PDF/DOC/client).
    
    INVARIANT: export autorisé ⟺ gate_passed = True ET can_release = True
    
    DOUBLE-CHECK V2: vérifie en plus que le rendered_contract
    ne contient pas de patterns P0 (défense en profondeur).
    
    Args:
        output: Le résultat du pipeline de rédaction
    
    Returns:
        True si l'export est autorisé, False sinon
    """
    if not output.gate_passed:
        logger.info(f"Export DENIED: gate_passed=False (corr: {output.draft.correlation_id})")
        return False
    if not output.gate_verdict.can_release:
        logger.warning(f"Export DENIED: can_release=False despite gate_passed=True (corr: {output.draft.correlation_id})")
        return False
    if output.gate_verdict.has_p0():
        logger.warning(f"Export DENIED: P0 present despite can_release=True (corr: {output.draft.correlation_id})")
        return False
    if not output.rendered_contract:
        logger.info(f"Export DENIED: rendered_contract is empty (corr: {output.draft.correlation_id})")
        return False

    # ─── DOUBLE-CHECK V2: Re-scan final output for P0 (defense in depth) ───
    try:
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        final_findings = scan_for_leaks(output.rendered_contract, section="EXPORT_FINAL_CHECK")
        final_p0s = [f for f in final_findings if f.severity == FindingSeverity.P0]
        if final_p0s:
            logger.error(
                f"Export DENIED (defense-in-depth): {len(final_p0s)} P0 found in final output "
                f"despite gate PASS (corr: {output.draft.correlation_id}). "
                f"Patterns: {[f.pattern for f in final_p0s]}"
            )
            return False
    except Exception as e:
        # Fail-closed: if we can't re-scan, deny export
        logger.error(f"Export DENIED: re-scan failed (fail-closed): {e}")
        return False

    return True


def get_export_stamp(output: "DraftingOutput") -> str:
    """Génère le stamp d'export si autorisé.
    
    HARDENED V2: inclut les versions des templates utilisés.
    
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
    
    # Template versions
    version_lines = []
    try:
        from python.helpers.contract_drafting.templates import get_template_versions
        versions = get_template_versions()
        for section, tv in sorted(versions.items()):
            version_lines.append(f"    {section}: v{tv.version} ({tv.last_review_date})")
    except Exception:
        version_lines.append("    [versions non disponibles]")
    
    versions_block = "\n".join(version_lines)
    
    return (
        f"══════════════════════════════════════════════\n"
        f"  VALIDÉ PAR LEGAL_SAFE GATE — PASS{p1_mention}\n"
        f"  Date: {now}\n"
        f"  Correlation ID: {output.draft.correlation_id}\n"
        f"  Templates:\n{versions_block}\n"
        f"  PROJET — À VALIDER PAR UN JURISTE QUALIFIÉ\n"
        f"══════════════════════════════════════════════"
    )

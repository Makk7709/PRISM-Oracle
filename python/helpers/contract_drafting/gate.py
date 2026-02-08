"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           GATE D'AUDIT — Fail-Closed Contract Gate                          ║
║                                                                              ║
║  Pipeline: Draft → GATE → Output                                            ║
║                                                                              ║
║  INVARIANTS:                                                                 ║
║    1. P0 trouvé ⟹ REJECT (can_release = False)                             ║
║    2. Disclaimer absent ⟹ REJECT                                            ║
║    3. can_release = True ⟺ verdict = APPROVE                               ║
║    4. Fail-closed : tout doute ⟹ REJECT                                    ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import List

from python.helpers.contract_drafting.leak_guard import scan_for_leaks_by_section
from python.helpers.contract_drafting.models import (
    ContractDraft,
    FindingSeverity,
    GateVerdict,
    GateVerdictEnum,
    LeakFinding,
)


def run_gate(draft: ContractDraft) -> GateVerdict:
    """Exécute la gate d'audit sur un brouillon de contrat.
    
    INVARIANTS ENFORCED:
        - P0 trouvé ⟹ REJECT (can_release = False)
        - Disclaimer absent ⟹ REJECT
        - can_release = True ⟺ verdict = APPROVE
    
    Args:
        draft: Le brouillon de contrat à auditer
    
    Returns:
        GateVerdict avec verdict, findings et can_release
    """
    findings: List[LeakFinding] = []
    reject_reasons: List[str] = []
    
    # ─── CHECK 1: Disclaimer obligatoire ───
    if not draft.disclaimer or not draft.disclaimer.strip():
        reject_reasons.append("Disclaimer absent ou vide")
        findings.append(LeakFinding(
            severity=FindingSeverity.P0,
            pattern="disclaimer_missing",
            context="Le brouillon ne contient pas de disclaimer 'PROJET — à valider'",
            recommendation="Ajouter le disclaimer: 'PROJET — À VALIDER PAR UN JURISTE QUALIFIÉ'",
            section="METADATA",
        ))
    
    # ─── CHECK 2: Scan Leak Guard sur toutes les sections ───
    leak_findings = scan_for_leaks_by_section(draft.sections)
    findings.extend(leak_findings)
    
    # ─── CHECK 3: Évaluation du verdict ───
    has_p0 = any(f.severity == FindingSeverity.P0 for f in findings)
    p0_count = sum(1 for f in findings if f.severity == FindingSeverity.P0)
    p1_count = sum(1 for f in findings if f.severity == FindingSeverity.P1)
    
    if has_p0:
        reject_reasons.append(f"{p0_count} finding(s) P0 bloquant(s)")
    
    # ─── VERDICT ───
    if reject_reasons:
        return GateVerdict(
            verdict=GateVerdictEnum.REJECT,
            findings=findings,
            can_release=False,  # INVARIANT: REJECT ⟹ can_release = False
            summary=f"REJETÉ — {'; '.join(reject_reasons)}. "
                    f"P0: {p0_count}, P1: {p1_count}. "
                    f"Corrections requises avant release.",
        )
    
    # Pas de P0, pas de reject — APPROVE
    summary_parts = ["APPROUVÉ"]
    if p1_count > 0:
        summary_parts.append(f"avec {p1_count} avertissement(s) P1")
    
    return GateVerdict(
        verdict=GateVerdictEnum.APPROVE,
        findings=findings,
        can_release=True,  # INVARIANT: APPROVE ⟹ can_release = True
        summary=" ".join(summary_parts),
    )

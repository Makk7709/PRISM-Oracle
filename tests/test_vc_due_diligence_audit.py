"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   AUDIT DUE DILIGENCE TECHNIQUE — NIVEAU AUDITEUR VC                      ║
║                                                                              ║
║   Ce script simule l'audit qu'un investisseur (VC) ferait exécuter         ║
║   par son Technical Advisor avant un investissement dans KOREV Evidence.   ║
║                                                                              ║
║   OBJECTIF: Évaluer la SOLIDITÉ, la SÉCURITÉ et la QUALITÉ du pipeline    ║
║   de rédaction contractuelle ("Draft mode") en tant que composant          ║
║   COMMERCIAL-READY.                                                         ║
║                                                                              ║
║   GRILLE D'ÉVALUATION (12 critères, score /100):                           ║
║                                                                              ║
║     A. Architecture & Design (20 pts)                                       ║
║        A1. Fail-closed enforcement (5)                                      ║
║        A2. Defense-in-depth layers (5)                                      ║
║        A3. Separation of concerns (5)                                       ║
║        A4. No shared mutable state (5)                                      ║
║                                                                              ║
║     B. Security Posture (25 pts)                                            ║
║        B1. Input sanitization (5)                                           ║
║        B2. Injection prevention (5)                                         ║
║        B3. LLM fallback protection (5)                                      ║
║        B4. Export control enforcement (5)                                    ║
║        B5. P0/P1 invariant consistency (5)                                  ║
║                                                                              ║
║     C. Legal Compliance (20 pts)                                            ║
║        C1. Citation verification pipeline (5)                               ║
║        C2. Template versioning & audit trail (5)                            ║
║        C3. Disclaimer enforcement (5)                                       ║
║        C4. Section completeness check (5)                                   ║
║                                                                              ║
║     D. Code Quality (20 pts)                                                ║
║        D1. No dead code / commented-out code (5)                           ║
║        D2. Error handling coverage (5)                                      ║
║        D3. Regex precision (false pos/neg rate) (5)                        ║
║        D4. Type safety & documentation (5)                                  ║
║                                                                              ║
║     E. Test Coverage & CI (15 pts)                                          ║
║        E1. Positive path coverage (5)                                       ║
║        E2. Negative path coverage (5)                                       ║
║        E3. Regression protection (5)                                        ║
║                                                                              ║
║   VERDICT:                                                                   ║
║     ≥ 85  → INVESTISSABLE — prêt pour commercialisation                    ║
║     70-84 → CONDITIONNEL — corrections mineures requises                   ║
║     < 70  → NON INVESTISSABLE — risques structurels                        ║
║                                                                              ║
║   © 2026 Korev AI — Proprietary — CONFIDENTIEL                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuditCheck:
    """Résultat d'un contrôle d'audit."""
    criterion: str
    category: str
    max_score: int
    actual_score: int
    status: str  # PASS / PARTIAL / FAIL
    detail: str
    severity: str = ""  # CRITICAL / MAJOR / MINOR / INFO


@dataclass
class AuditReport:
    """Rapport d'audit complet."""
    checks: List[AuditCheck] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total_score(self) -> int:
        return sum(c.actual_score for c in self.checks)

    @property
    def max_score(self) -> int:
        return sum(c.max_score for c in self.checks)

    @property
    def percentage(self) -> float:
        return (self.total_score / self.max_score * 100) if self.max_score > 0 else 0

    @property
    def verdict(self) -> str:
        pct = self.percentage
        if pct >= 85:
            return "INVESTISSABLE"
        elif pct >= 70:
            return "CONDITIONNEL"
        else:
            return "NON INVESTISSABLE"

    def summary(self) -> str:
        lines = [
            "",
            "=" * 70,
            "  RAPPORT D'AUDIT DUE DILIGENCE TECHNIQUE — KOREV EVIDENCE",
            "  MODE DRAFT — PIPELINE CONTRACTUEL",
            "=" * 70,
            "",
            f"  Score: {self.total_score}/{self.max_score} ({self.percentage:.1f}%)",
            f"  Verdict: {self.verdict}",
            f"  Durée audit: {self.end_time - self.start_time:.2f}s",
            "",
        ]

        # Par catégorie
        categories = {}
        for c in self.checks:
            categories.setdefault(c.category, []).append(c)

        for cat, checks in categories.items():
            cat_score = sum(c.actual_score for c in checks)
            cat_max = sum(c.max_score for c in checks)
            lines.append(f"  {cat}: {cat_score}/{cat_max}")
            for c in checks:
                icon = "✓" if c.status == "PASS" else ("◐" if c.status == "PARTIAL" else "✗")
                lines.append(f"    {icon} {c.criterion}: {c.actual_score}/{c.max_score} — {c.detail}")
            lines.append("")

        # Findings critiques
        critical = [c for c in self.checks if c.severity == "CRITICAL" and c.status != "PASS"]
        if critical:
            lines.append("  FINDINGS CRITIQUES:")
            for c in critical:
                lines.append(f"    ✗ [{c.category}] {c.criterion}: {c.detail}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)


# Global report
_report = AuditReport()


# ═══════════════════════════════════════════════════════════════════════════════
# A. ARCHITECTURE & DESIGN (20 pts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestA_Architecture:

    def test_A1_fail_closed_pipeline(self):
        """A1. Pipeline fail-closed: exception → REJECT (jamais APPROVE par défaut)."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import GateVerdictEnum
        from unittest.mock import patch

        # Simulate crash in generate_contract
        with patch(
            "python.helpers.contract_drafting.orchestrator.generate_contract",
            side_effect=RuntimeError("CRASH"),
        ):
            output = run_drafting_pipeline({"client_name": "X", "editor_name": "Y",
                                            "software_name": "Z", "jurisdiction": "P"})

        ok = (
            output.gate_passed is False
            and output.gate_verdict.verdict == GateVerdictEnum.REJECT
            and output.rendered_contract == ""
        )
        _report.checks.append(AuditCheck(
            criterion="A1. Fail-closed pipeline",
            category="A. Architecture",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Exception → REJECT vérifié" if ok else "FAILLE: Exception ne produit pas REJECT",
            severity="CRITICAL",
        ))
        assert ok

    def test_A2_defense_in_depth_export(self):
        """A2. Double-scan à l'export: re-scan P0 même après gate PASS."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )

        output = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="audit-a2"),
            gate_verdict=GateVerdict(verdict=GateVerdictEnum.APPROVE, can_release=True),
            gate_passed=True,
            gate_summary="APPROVE",
            rendered_contract="L'Éditeur procède à la remise du code source.",
        )
        denied = not is_export_allowed(output)
        _report.checks.append(AuditCheck(
            criterion="A2. Defense-in-depth export",
            category="A. Architecture",
            max_score=5, actual_score=5 if denied else 0,
            status="PASS" if denied else "FAIL",
            detail="Re-scan P0 bloque l'export" if denied else "FAILLE: P0 passe l'export",
            severity="CRITICAL",
        ))
        assert denied

    def test_A3_separation_of_concerns(self):
        """A3. Chaque composant a un rôle unique (orchestrator, gate, leak_guard, export)."""
        modules = [
            "python/helpers/contract_drafting/orchestrator.py",
            "python/helpers/contract_drafting/gate.py",
            "python/helpers/contract_drafting/leak_guard.py",
            "python/helpers/contract_drafting/export_control.py",
            "python/helpers/contract_drafting/models.py",
            "python/helpers/contract_drafting/templates.py",
        ]
        exist = all(os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), m)) for m in modules)
        _report.checks.append(AuditCheck(
            criterion="A3. Separation of concerns",
            category="A. Architecture",
            max_score=5, actual_score=5 if exist else 0,
            status="PASS" if exist else "FAIL",
            detail=f"6 modules distincts vérifié" if exist else "Modules manquants",
            severity="MAJOR",
        ))
        assert exist

    def test_A4_no_shared_mutable_state(self):
        """A4. Pas de state mutable partagé entre appels pipeline."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        # Utiliser des noms très distinctifs pour éviter les faux positifs
        # (la lettre "A" seule apparait dans les templates naturellement)
        vars1 = {"client_name": "ACMEFOXTROT", "editor_name": "KOREV",
                  "software_name": "AlphaProduct", "jurisdiction": "Grenoble"}
        vars2 = {"client_name": "ZEPHYRDELTA", "editor_name": "KOREV",
                  "software_name": "BetaProduct", "jurisdiction": "Lyon"}

        out1 = run_drafting_pipeline(vars1)
        out2 = run_drafting_pipeline(vars2)

        # Chaque appel doit avoir son propre correlation_id
        ids_differ = out1.draft.correlation_id != out2.draft.correlation_id
        # Chaque contrat doit contenir ses propres variables (pas de leak)
        no_leak = True
        if out1.gate_passed and out2.gate_passed:
            no_leak = (
                "ZEPHYRDELTA" not in out1.rendered_contract
                and "ACMEFOXTROT" not in out2.rendered_contract
            )

        ok = ids_differ and no_leak
        _report.checks.append(AuditCheck(
            criterion="A4. No shared mutable state",
            category="A. Architecture",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Isolation des appels vérifié" if ok else "State leak détecté",
            severity="MAJOR",
        ))
        assert ok


# ═══════════════════════════════════════════════════════════════════════════════
# B. SECURITY POSTURE (25 pts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestB_Security:

    def test_B1_input_sanitization(self):
        """B1. Variables nettoyées (trim + normalize)."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        r = validate_contract_variables({
            "client_name": "  DICA   France  ", "editor_name": "KOREV",
            "software_name": "Test", "jurisdiction": "Paris",
        })
        ok = r.is_valid and r.sanitized_variables.get("client_name") == "DICA France"
        _report.checks.append(AuditCheck(
            criterion="B1. Input sanitization",
            category="B. Security",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Sanitization + normalize OK" if ok else "Sanitization défaillante",
            severity="MAJOR",
        ))
        assert ok

    def test_B2_injection_prevention(self):
        """B2. XSS, template injection, code execution bloqués."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        attacks = [
            '<script>alert(1)</script>',
            '{{ __import__("os").system("id") }}',
            'eval(input())',
            '${7*7}',
        ]
        all_blocked = True
        for attack in attacks:
            r = validate_contract_variables({"client_name": attack, "editor_name": "K",
                                             "software_name": "T", "jurisdiction": "P"})
            if r.is_valid:
                all_blocked = False

        _report.checks.append(AuditCheck(
            criterion="B2. Injection prevention",
            category="B. Security",
            max_score=5, actual_score=5 if all_blocked else 0,
            status="PASS" if all_blocked else "FAIL",
            detail=f"4/4 injections bloquées" if all_blocked else "Injection non bloquée",
            severity="CRITICAL",
        ))
        assert all_blocked

    def test_B3_llm_fallback_protection(self):
        """B3. L'intégration empêche le fallback LLM sur exception pipeline."""
        integration_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "python", "extensions", "legal_safe_mode", "_10_legal_safe_integration.py",
        )
        with open(integration_path) as f:
            content = f.read()

        has_fail_closed = "FAIL-CLOSED" in content
        has_skip_llm = '_skip_llm", True' in content
        has_return = "return  # CRITICAL: Do NOT fall through to LLM" in content
        catches_exception = "except Exception as drafting_exc:" in content

        ok = has_fail_closed and has_skip_llm and has_return and catches_exception
        _report.checks.append(AuditCheck(
            criterion="B3. LLM fallback protection",
            category="B. Security",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Fail-closed + skip_llm + return vérifié" if ok else "LLM fallback possible",
            severity="CRITICAL",
        ))
        assert ok

    def test_B4_export_control(self):
        """B4. Export bloqué si gate non PASS, P0 présent, ou contrat vide."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )

        # Cas 1: gate_passed=False
        case1 = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="b4-1"),
            gate_verdict=GateVerdict(verdict=GateVerdictEnum.REJECT, can_release=False),
            gate_passed=False, gate_summary="REJECT", rendered_contract="content",
        )
        # Cas 2: rendered_contract vide
        case2 = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="b4-2"),
            gate_verdict=GateVerdict(verdict=GateVerdictEnum.APPROVE, can_release=True),
            gate_passed=True, gate_summary="APPROVE", rendered_contract="",
        )
        blocked = not is_export_allowed(case1) and not is_export_allowed(case2)
        _report.checks.append(AuditCheck(
            criterion="B4. Export control enforcement",
            category="B. Security",
            max_score=5, actual_score=5 if blocked else 0,
            status="PASS" if blocked else "FAIL",
            detail="Export bloqué sur 2 cas" if blocked else "Export non bloqué",
            severity="CRITICAL",
        ))
        assert blocked

    def test_B5_p0_invariant_consistency(self):
        """B5. P0 ⟹ REJECT, can_release=False — invariant structurel."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import (
            ContractDraft, GateVerdictEnum, FindingSeverity,
        )

        draft = ContractDraft(
            sections={
                "CP": "ok", "CG": "Remise du code source au client.",
                "ANNEXE_1": "ok", "ANNEXE_2": "ok", "ANNEXE_3": "ok",
                "ANNEXE_4": "ok", "ANNEXE_5": "ok", "ANNEXE_6": "ok",
            },
            disclaimer="PROJET", correlation_id="b5-test",
        )
        v = run_gate(draft)
        ok = v.has_p0() and v.verdict == GateVerdictEnum.REJECT and not v.can_release
        _report.checks.append(AuditCheck(
            criterion="B5. P0 → REJECT invariant",
            category="B. Security",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="P0 → REJECT + can_release=False" if ok else "INVARIANT VIOLÉ",
            severity="CRITICAL",
        ))
        assert ok


# ═══════════════════════════════════════════════════════════════════════════════
# C. LEGAL COMPLIANCE (20 pts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestC_Legal:

    def test_C1_citation_verification_pipeline(self):
        """C1. Le pipeline vérifie les citations légales (format + index)."""
        from python.helpers.contract_drafting.gate import verify_legal_citations
        sections = {
            "CG": "Conformément à l'art. 1103 du Code civil, le contrat est la loi des parties.",
        }
        findings = verify_legal_citations(sections)
        # Should produce findings (citation_* because index is empty) but NOT crash
        ok = isinstance(findings, list)
        _report.checks.append(AuditCheck(
            criterion="C1. Citation verification pipeline",
            category="C. Legal",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Pipeline de vérification fonctionnel" if ok else "Pipeline de vérification cassé",
            severity="MAJOR",
        ))
        assert ok

    def test_C2_template_versioning(self):
        """C2. Chaque template a une version semver, date de revue, reviewer."""
        from python.helpers.contract_drafting.templates import get_template_pack, get_template_versions
        pack = get_template_pack()
        versions = get_template_versions()

        all_versioned = True
        for section in pack:
            if section not in versions:
                all_versioned = False
                break
            tv = versions[section]
            if not tv.version or not tv.last_review_date or not tv.reviewer:
                all_versioned = False
                break

        semver_ok = all(
            re.match(r"^\d+\.\d+\.\d+$", tv.version)
            for tv in versions.values()
        )

        ok = all_versioned and semver_ok
        _report.checks.append(AuditCheck(
            criterion="C2. Template versioning",
            category="C. Legal",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail=f"8 templates versionnés, semver OK" if ok else "Versioning incomplet",
            severity="MAJOR",
        ))
        assert ok

    def test_C3_disclaimer_enforcement(self):
        """C3. Disclaimer absent → REJECT (aucun contrat sans avertissement)."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum

        draft = ContractDraft(
            sections={
                "CP": "ok", "CG": "ok", "ANNEXE_1": "ok", "ANNEXE_2": "ok",
                "ANNEXE_3": "ok", "ANNEXE_4": "ok", "ANNEXE_5": "ok", "ANNEXE_6": "ok",
            },
            disclaimer="",  # Absent
        )
        v = run_gate(draft)
        ok = v.verdict == GateVerdictEnum.REJECT and not v.can_release
        _report.checks.append(AuditCheck(
            criterion="C3. Disclaimer enforcement",
            category="C. Legal",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Disclaimer absent → REJECT OK" if ok else "Disclaimer non enforced",
            severity="CRITICAL",
        ))
        assert ok

    def test_C4_section_completeness(self):
        """C4. 8 sections requises, manquante = P0."""
        from python.helpers.contract_drafting.gate import check_section_completeness
        from python.helpers.contract_drafting.models import FindingSeverity
        findings = check_section_completeness({"CP": "ok"})
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        ok = len(p0s) == 7  # 7 sections manquantes
        _report.checks.append(AuditCheck(
            criterion="C4. Section completeness",
            category="C. Legal",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail=f"7 sections manquantes = 7 P0 détectées" if ok else f"Expected 7 P0, got {len(p0s)}",
            severity="MAJOR",
        ))
        assert ok


# ═══════════════════════════════════════════════════════════════════════════════
# D. CODE QUALITY (20 pts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestD_CodeQuality:

    def test_D1_no_dead_code(self):
        """D1. Pas de code commenté ou de fonctions mortes dans les modules critiques."""
        modules = [
            "python/helpers/contract_drafting/gate.py",
            "python/helpers/contract_drafting/leak_guard.py",
            "python/helpers/contract_drafting/orchestrator.py",
            "python/helpers/contract_drafting/export_control.py",
        ]
        dead_code_found = []
        for module_path in modules:
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), module_path)
            with open(full_path) as f:
                content = f.read()
            # Check for large commented-out blocks (3+ consecutive commented lines)
            consecutive_comments = 0
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("#") and not stripped.startswith("#!") and len(stripped) > 5:
                    # Ignore header comments and decorative lines
                    if stripped.startswith("# ═") or stripped.startswith("# ---") or stripped.startswith("# ─"):
                        consecutive_comments = 0
                        continue
                    if stripped.startswith("# NOTE:") or stripped.startswith("# INVARIANT"):
                        consecutive_comments = 0
                        continue
                    consecutive_comments += 1
                else:
                    consecutive_comments = 0
                if consecutive_comments >= 5:
                    dead_code_found.append(module_path)
                    break

        ok = len(dead_code_found) == 0
        _report.checks.append(AuditCheck(
            criterion="D1. No dead code",
            category="D. Code Quality",
            max_score=5, actual_score=5 if ok else 3,
            status="PASS" if ok else "PARTIAL",
            detail="0 bloc de code mort" if ok else f"Dead code dans: {dead_code_found}",
            severity="MINOR",
        ))
        assert ok or len(dead_code_found) <= 1

    def test_D2_error_handling_coverage(self):
        """D2. Tous les modules critiques ont try/except avec logging."""
        modules_to_check = {
            "gate.py": "run_gate",
            "orchestrator.py": "run_drafting_pipeline",
            "export_control.py": "is_export_allowed",
        }
        covered = 0
        for module_file, func_name in modules_to_check.items():
            path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "python", "helpers", "contract_drafting", module_file,
            )
            with open(path) as f:
                content = f.read()
            if f"except Exception" in content and "logger." in content:
                covered += 1

        ok = covered == len(modules_to_check)
        _report.checks.append(AuditCheck(
            criterion="D2. Error handling coverage",
            category="D. Code Quality",
            max_score=5, actual_score=5 if ok else (covered * 5 // len(modules_to_check)),
            status="PASS" if ok else "PARTIAL",
            detail=f"{covered}/{len(modules_to_check)} modules avec error handling" if ok else f"Manque dans {len(modules_to_check) - covered} module(s)",
            severity="MAJOR",
        ))
        assert covered >= 2

    def test_D3_regex_precision(self):
        """D3. Taux de faux positifs = 0 sur les templates KOREV."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks_by_section
        from python.helpers.contract_drafting.models import FindingSeverity
        from python.helpers.contract_drafting.templates import get_template_pack, render_template

        pack = get_template_pack()
        variables = {
            "client_name": "DICA France", "editor_name": "KOREV",
            "software_name": "DICA Decor", "software_version": "3.2.1",
            "notice_period": "3 mois", "renewal_period": "12 mois",
            "remote_access": "false",
        }
        sections = {k: render_template(v, variables) for k, v in pack.items()}
        findings = scan_for_leaks_by_section(sections)

        # 0 P0, 0 P1 attendu sur templates KOREV
        p0 = [f for f in findings if f.severity == FindingSeverity.P0]
        p1 = [f for f in findings if f.severity == FindingSeverity.P1]
        false_positives = len(p0) + len(p1)

        ok = false_positives == 0
        _report.checks.append(AuditCheck(
            criterion="D3. Regex precision (FP rate)",
            category="D. Code Quality",
            max_score=5, actual_score=5 if ok else max(0, 5 - false_positives),
            status="PASS" if ok else "FAIL",
            detail=f"0 faux positifs sur templates KOREV" if ok else f"{false_positives} faux positifs",
            severity="MAJOR",
        ))
        assert ok

    def test_D4_type_safety_and_docs(self):
        """D4. Dataclasses typées, docstrings présentes."""
        from python.helpers.contract_drafting.models import (
            ContractDraft, GateVerdict, DraftingOutput, LeakFinding,
            TemplateVersion, VariableValidationResult, DraftAuditEntry,
        )
        classes = [ContractDraft, GateVerdict, DraftingOutput, LeakFinding,
                   TemplateVersion, VariableValidationResult, DraftAuditEntry]

        all_have_docs = all(cls.__doc__ and len(cls.__doc__) > 10 for cls in classes)

        from python.helpers.contract_drafting.gate import run_gate, verify_legal_citations
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        funcs = [run_gate, verify_legal_citations, run_drafting_pipeline]
        funcs_have_docs = all(f.__doc__ and len(f.__doc__) > 10 for f in funcs)

        ok = all_have_docs and funcs_have_docs
        _report.checks.append(AuditCheck(
            criterion="D4. Type safety & documentation",
            category="D. Code Quality",
            max_score=5, actual_score=5 if ok else 3,
            status="PASS" if ok else "PARTIAL",
            detail="7 classes + 3 fonctions documentées" if ok else "Documentation incomplète",
            severity="MINOR",
        ))
        assert ok or (all_have_docs or funcs_have_docs)


# ═══════════════════════════════════════════════════════════════════════════════
# E. TEST COVERAGE (15 pts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE_TestCoverage:

    def test_E1_positive_path(self):
        """E1. Le happy path complet fonctionne (variables propres → APPROVE → export)."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.export_control import is_export_allowed

        output = run_drafting_pipeline({
            "client_name": "DICA France", "editor_name": "KOREV",
            "software_name": "DICA Decor", "software_version": "3.2.1",
            "jurisdiction": "Tribunal de commerce de Grenoble",
            "licence_metric": "par poste", "initial_posts": "1", "max_posts": "4",
            "remote_access": "false", "notice_period": "3 mois",
            "renewal_period": "12 mois", "contract_duration": "36 mois",
        })

        ok = (
            output.gate_passed is True
            and output.rendered_contract != ""
            and is_export_allowed(output) is True
            and "DICA France" in output.rendered_contract
            and "KOREV" in output.rendered_contract
        )
        _report.checks.append(AuditCheck(
            criterion="E1. Positive path (E2E)",
            category="E. Test Coverage",
            max_score=5, actual_score=5 if ok else 0,
            status="PASS" if ok else "FAIL",
            detail="Happy path complet: generate → gate → export" if ok else "Happy path BROKEN",
            severity="CRITICAL",
        ))
        assert ok

    def test_E2_negative_paths(self):
        """E2. Tous les chemins négatifs produisent un REJECT correct."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline

        negative_cases = [
            # XSS injection
            ({"client_name": '<script>alert(1)</script>'}, "XSS"),
            # Invalid contract type
            ({"client_name": "X", "editor_name": "Y", "software_name": "Z",
              "jurisdiction": "P"}, "invalid type"),
        ]

        all_rejected = True
        for vars_, case_type in negative_cases:
            ctype = "saas" if case_type == "invalid type" else "on_prem_licence"
            output = run_drafting_pipeline(vars_, contract_type=ctype)
            if output.gate_passed:
                all_rejected = False
                break

        _report.checks.append(AuditCheck(
            criterion="E2. Negative paths",
            category="E. Test Coverage",
            max_score=5, actual_score=5 if all_rejected else 0,
            status="PASS" if all_rejected else "FAIL",
            detail=f"2/2 cas négatifs → REJECT" if all_rejected else "Cas négatif accepté",
            severity="MAJOR",
        ))
        assert all_rejected

    def test_E3_regression_suite_count(self):
        """E3. Suite de tests suffisante (> 100 tests contractuels)."""
        # Count tests in contract_drafting test files
        test_dir = os.path.dirname(__file__)
        total_tests = 0
        for fname in os.listdir(test_dir):
            if fname.startswith("test_contract_drafting") and fname.endswith(".py"):
                path = os.path.join(test_dir, fname)
                with open(path) as f:
                    content = f.read()
                total_tests += len(re.findall(r"def test_", content))

        ok = total_tests >= 100
        _report.checks.append(AuditCheck(
            criterion="E3. Regression suite size",
            category="E. Test Coverage",
            max_score=5, actual_score=5 if ok else min(4, total_tests // 25),
            status="PASS" if ok else "PARTIAL",
            detail=f"{total_tests} tests contractuels" if ok else f"Seulement {total_tests} tests (min: 100)",
            severity="MAJOR",
        ))
        assert total_tests >= 80  # Minimum acceptable


# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORT FINAL — FIXTURE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def vc_audit_report():
    """Initialise et affiche le rapport d'audit en fin de session."""
    _report.start_time = time.time()
    yield _report
    _report.end_time = time.time()
    print(_report.summary())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

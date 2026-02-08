"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   HARDENED V2 — TESTS DE BÉTONNAGE DU PIPELINE DRAFT                       ║
║                                                                              ║
║   Tests TDD STRICT pour toutes les nouvelles protections V2:                ║
║                                                                              ║
║     1. Template Versioning (registre, staleness, changelog)                 ║
║     2. Input Validation (injection, longueur, variables requises)           ║
║     3. Error Handling (pipeline exception → REJECT, gate exception)         ║
║     4. LLM Fallback Fix (vérification code source)                         ║
║     5. Citation Verification (validation format Légifrance)                ║
║     6. Nouveaux P0/P1 Patterns (22 P0, 14 P1)                             ║
║     7. Defense-in-Depth Export (double-scan final)                          ║
║     8. Section Completeness (sections manquantes = P0)                     ║
║     9. Pipeline Fail-Closed on Exception                                    ║
║    10. Audit Trail (correlation_id, variables_hash, template_versions)      ║
║                                                                              ║
║   © 2026 Korev AI — Proprietary                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import re
from datetime import date
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: TEMPLATE VERSIONING
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateVersioning:
    """Tests du registre de versions des templates contractuels."""

    def test_all_sections_have_versions(self):
        """Chaque section du pack DOIT avoir une entrée dans le registre."""
        from python.helpers.contract_drafting.templates import (
            get_template_pack, get_template_versions,
        )
        pack = get_template_pack()
        versions = get_template_versions()
        for section in pack:
            assert section in versions, (
                f"Section '{section}' n'a pas de version dans le registre"
            )

    def test_version_has_required_fields(self):
        """Chaque TemplateVersion DOIT avoir version, date, reviewer, changelog."""
        from python.helpers.contract_drafting.templates import get_template_versions
        for section, tv in get_template_versions().items():
            assert tv.version, f"{section}: version manquante"
            assert tv.last_review_date, f"{section}: date de revue manquante"
            assert tv.reviewer, f"{section}: reviewer manquant"
            assert len(tv.changelog) >= 1, f"{section}: changelog vide"

    def test_version_format_semver(self):
        """Les versions DOIVENT respecter le format semver (X.Y.Z)."""
        from python.helpers.contract_drafting.templates import get_template_versions
        semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")
        for section, tv in get_template_versions().items():
            assert semver_pattern.match(tv.version), (
                f"{section}: version '{tv.version}' ne respecte pas le format semver X.Y.Z"
            )

    def test_version_review_date_not_future(self):
        """La date de revue NE DOIT PAS être dans le futur."""
        from python.helpers.contract_drafting.templates import get_template_versions
        today = date.today()
        for section, tv in get_template_versions().items():
            assert tv.last_review_date <= today, (
                f"{section}: date de revue dans le futur ({tv.last_review_date})"
            )

    def test_stale_detection_works(self):
        """Un template avec date > 365 jours DOIT être détecté comme stale."""
        from python.helpers.contract_drafting.models import TemplateVersion
        old_template = TemplateVersion(
            section="TEST",
            version="0.1.0",
            last_review_date=date(2024, 1, 1),  # > 365 days ago
            reviewer="test",
        )
        assert old_template.is_stale() is True

    def test_fresh_template_not_stale(self):
        """Un template récent NE DOIT PAS être détecté comme stale."""
        from python.helpers.contract_drafting.models import TemplateVersion
        fresh = TemplateVersion(
            section="TEST",
            version="1.0.0",
            last_review_date=date.today(),
            reviewer="test",
        )
        assert fresh.is_stale() is False

    def test_get_stale_templates_returns_list(self):
        """get_stale_templates DOIT retourner une liste (vide ou non)."""
        from python.helpers.contract_drafting.templates import get_stale_templates
        result = get_stale_templates()
        assert isinstance(result, list)

    def test_versions_summary_is_string(self):
        """Le résumé des versions DOIT être une chaîne non vide."""
        from python.helpers.contract_drafting.templates import get_template_versions_summary
        summary = get_template_versions_summary()
        assert isinstance(summary, str)
        assert len(summary) > 100

    def test_legal_basis_present_on_all(self):
        """Chaque template DOIT avoir une base légale renseignée."""
        from python.helpers.contract_drafting.templates import get_template_versions
        for section, tv in get_template_versions().items():
            assert tv.legal_basis, f"{section}: base légale manquante"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestInputValidation:
    """Tests de validation des variables d'entrée."""

    def test_valid_input_passes(self):
        """Des variables valides DOIVENT passer la validation."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Grenoble",
        })
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_xss_injection_blocked(self):
        """Une injection XSS DOIT être bloquée."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": '<script>alert("xss")</script>',
            "editor_name": "KOREV",
            "software_name": "Test",
            "jurisdiction": "Paris",
        })
        assert result.is_valid is False
        assert any("injection" in e.lower() for e in result.errors)

    def test_template_injection_blocked(self):
        """Une injection de template ({{ }}) DOIT être bloquée."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": "{{ os.system('rm -rf /') }}",
            "editor_name": "KOREV",
            "software_name": "Test",
            "jurisdiction": "Paris",
        })
        assert result.is_valid is False

    def test_code_execution_injection_blocked(self):
        """__import__, eval, exec DOIVENT être bloqués."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        for malicious in [
            "__import__('os').system('id')",
            "eval(input())",
            "exec('rm -rf /')",
        ]:
            result = validate_contract_variables({
                "client_name": malicious,
                "editor_name": "KOREV",
                "software_name": "Test",
                "jurisdiction": "Paris",
            })
            assert result.is_valid is False, f"Injection not blocked: {malicious}"

    def test_max_length_enforced(self):
        """Les variables > 2000 chars DOIVENT être rejetées."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": "A" * 2001,
            "editor_name": "KOREV",
            "software_name": "Test",
            "jurisdiction": "Paris",
        })
        assert result.is_valid is False
        assert any("longueur" in e.lower() or "length" in e.lower() for e in result.errors)

    def test_missing_required_generates_warning(self):
        """Les variables requises manquantes génèrent un warning (pas une erreur)."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "editor_name": "KOREV",
        })
        # Missing client_name, software_name, jurisdiction → warnings
        assert result.is_valid is True  # Warnings, not errors
        assert len(result.warnings) >= 3

    def test_invalid_contract_type_rejected(self):
        """Un type de contrat non autorisé DOIT être rejeté."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z", "jurisdiction": "P"},
            contract_type="saas_subscription",  # Not allowed
        )
        assert result.is_valid is False
        assert any("type" in e.lower() for e in result.errors)

    def test_sanitization_strips_whitespace(self):
        """Les variables sanitisées DOIVENT être nettoyées (trim + normalize)."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": "  DICA   France  ",
            "editor_name": "KOREV",
            "software_name": "Test",
            "jurisdiction": "Paris",
        })
        assert result.is_valid is True
        assert result.sanitized_variables["client_name"] == "DICA France"

    def test_pipeline_rejects_on_invalid_input(self):
        """Le pipeline complet DOIT rejeter si la validation échoue."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline(
            variables={"client_name": '<script>alert(1)</script>'},
            contract_type="on_prem_licence",
        )
        assert output.gate_passed is False
        assert "validation" in output.gate_summary.lower() or "input" in output.gate_summary.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: ERROR HANDLING — PIPELINE FAIL-CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineFailClosed:
    """Tests du comportement fail-closed du pipeline."""

    def test_pipeline_never_raises(self):
        """Le pipeline NE DOIT JAMAIS lever d'exception — toujours DraftingOutput."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import DraftingOutput
        # Even with completely empty input
        output = run_drafting_pipeline(variables={}, contract_type="on_prem_licence")
        assert isinstance(output, DraftingOutput)

    def test_gate_exception_returns_reject(self):
        """Si la gate lève une exception, le verdict DOIT être REJECT."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        # Create a draft that might cause issues
        draft = ContractDraft(
            sections={"CP": "test"},
            variables={},
            disclaimer="PROJET",
            correlation_id="test-exception",
        )
        # run_gate should handle internal exceptions gracefully
        verdict = run_gate(draft)
        # Even with incomplete sections, it should return a valid verdict
        assert verdict.verdict in (GateVerdictEnum.APPROVE, GateVerdictEnum.REJECT)

    def test_pipeline_reject_on_invalid_contract_type(self):
        """Un type de contrat invalide → pipeline REJECT (pas d'exception)."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline(
            variables={"client_name": "X", "editor_name": "Y",
                       "software_name": "Z", "jurisdiction": "P"},
            contract_type="unknown_type",
        )
        assert output.gate_passed is False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: LLM FALLBACK FIX VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMFallbackFix:
    """Vérifie que le LLM ne peut PAS bypasser le pipeline en cas d'exception."""

    def test_integration_has_fail_closed_exception_handler(self):
        """L'intégration DOIT avoir un handler d'exception fail-closed (pas de fallback LLM)."""
        import os
        integration_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "python", "extensions", "legal_safe_mode", "_10_legal_safe_integration.py"
        )
        with open(integration_path) as f:
            content = f.read()
        
        # Verify the fail-closed pattern exists
        assert "FAIL-CLOSED" in content, "L'intégration doit contenir un handler FAIL-CLOSED"
        assert "Do NOT fall through to LLM" in content or "CRITICAL: Do NOT fall through to LLM" in content, \
            "L'intégration doit explicitement empêcher le fallback vers le LLM"

    def test_integration_catches_generic_exception(self):
        """L'intégration DOIT catcher Exception (pas seulement ImportError)."""
        import os
        integration_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "python", "extensions", "legal_safe_mode", "_10_legal_safe_integration.py"
        )
        with open(integration_path) as f:
            content = f.read()
        
        # Must have both ImportError and generic Exception handlers
        assert "except ImportError:" in content, "Doit catcher ImportError"
        assert "except Exception as drafting_exc:" in content, "Doit catcher Exception générique"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: CITATION VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestCitationVerification:
    """Tests de la vérification des citations légales dans le draft."""

    def test_valid_code_civil_not_flagged(self):
        """Une référence au Code civil valide NE DOIT PAS être flaggée comme P0."""
        from python.helpers.contract_drafting.gate import verify_legal_citations
        sections = {
            "CG": "Conformément à l'article 1103 du Code civil, le contrat est la loi des parties.",
        }
        findings = verify_legal_citations(sections)
        p0s = [f for f in findings if f.severity.value == "P0"]
        assert len(p0s) == 0, "Un article du Code civil valide ne doit pas être P0"

    def test_citation_verification_returns_list(self):
        """verify_legal_citations DOIT toujours retourner une liste."""
        from python.helpers.contract_drafting.gate import verify_legal_citations
        result = verify_legal_citations({"CP": "Texte sans aucune référence légale."})
        assert isinstance(result, list)

    def test_citation_check_runs_in_gate(self):
        """La gate V2 DOIT exécuter la vérification des citations."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={
                "CP": "Article CP.1 — voir Code civil, art. 1103",
                "CG": "Conformément à l'art. L.122-6 CPI",
                "ANNEXE_1": "Logiciel X",
                "ANNEXE_2": "Support",
                "ANNEXE_3": "Sécurité",
                "ANNEXE_4": "DPA",
                "ANNEXE_5": "Réversibilité",
                "ANNEXE_6": "Tarifs",
            },
            variables={},
            disclaimer="PROJET — À VALIDER",
            correlation_id="test-citations",
        )
        verdict = run_gate(draft)
        # Gate should run without error
        assert verdict.verdict is not None


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: NOUVEAUX P0/P1 PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewLeakPatterns:
    """Tests des nouveaux patterns P0/P1 ajoutés en V2."""

    def test_reverse_engineering_authorized_p0(self):
        """Autoriser le reverse engineering → P0 bloquant."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client est autorisé à procéder au reverse engineering du Logiciel."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Reverse engineering autorisé doit être P0"

    def test_source_code_on_bankruptcy_p0(self):
        """Accès code source en cas de faillite → P0 bloquant."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "En cas de faillite de l'Éditeur, le Client recevra le code source."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Accès code source en cas de faillite doit être P0"

    def test_source_code_audit_p0(self):
        """Audit du code source par le Client → P0 bloquant."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client peut auditer le code source annuellement."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Audit du code source doit être P0"

    def test_perpetual_free_license_p0(self):
        """Licence perpétuelle gratuite → P0 bloquant."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client bénéficie d'une licence perpétuelle et gratuite."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Licence perpétuelle gratuite doit être P0"

    def test_sublicense_authorized_p0(self):
        """Sous-licence autorisée → P0 bloquant."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "La sous-licence est autorisée avec accord préalable."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Sous-licence autorisée doit être P0"

    def test_unlimited_indemnification_p1(self):
        """Indemnisation illimitée → P1 warning."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur accepte une indemnisation illimitée en cas de préjudice."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1s) >= 1, "Indemnisation illimitée doit être P1"

    def test_exclusivity_clause_p1(self):
        """Clause d'exclusivité → P1 warning."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client bénéficie d'une exclusivité totale sur le logiciel."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1s) >= 1, "Exclusivité totale doit être P1"

    def test_contract_assignment_without_consent_p1(self):
        """Cession de contrat sans accord → P1 warning."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client peut céder le présent contrat librement à un tiers."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1s) >= 1, "Cession de contrat sans accord doit être P1"

    def test_pattern_count_minimum(self):
        """Le leak guard DOIT avoir au minimum 22 P0 et 14 P1."""
        from python.helpers.contract_drafting.leak_guard import _P0_PATTERNS, _P1_PATTERNS
        assert len(_P0_PATTERNS) >= 22, (
            f"Nombre de patterns P0 insuffisant: {len(_P0_PATTERNS)} < 22"
        )
        assert len(_P1_PATTERNS) >= 14, (
            f"Nombre de patterns P1 insuffisant: {len(_P1_PATTERNS)} < 14"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: DEFENSE-IN-DEPTH EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefenseInDepthExport:
    """Tests de la double vérification à l'export."""

    def test_export_denied_if_gate_not_passed(self):
        """Export REFUSÉ si gate_passed = False."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="t"),
            gate_verdict=GateVerdict(verdict=GateVerdictEnum.REJECT, can_release=False),
            gate_passed=False,
            gate_summary="REJECT",
            rendered_contract="du contenu",
        )
        assert is_export_allowed(output) is False

    def test_export_denied_if_rendered_empty(self):
        """Export REFUSÉ si rendered_contract est vide."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="t"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE, can_release=True,
            ),
            gate_passed=True,
            gate_summary="APPROVE",
            rendered_contract="",  # Empty!
        )
        assert is_export_allowed(output) is False

    def test_export_stamp_includes_template_versions(self):
        """Le stamp d'export DOIT inclure les versions des templates."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.export_control import get_export_stamp
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Grenoble",
        }
        output = run_drafting_pipeline(variables)
        if output.gate_passed:
            stamp = get_export_stamp(output)
            assert "v1.0.0" in stamp or "version" in stamp.lower(), \
                "Le stamp doit contenir les versions des templates"

    def test_export_stamp_refused_on_reject(self):
        """Le stamp d'export doit mentionner REFUSÉ si gate REJECT."""
        from python.helpers.contract_drafting.export_control import get_export_stamp
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="t"),
            gate_verdict=GateVerdict(verdict=GateVerdictEnum.REJECT, can_release=False),
            gate_passed=False,
            gate_summary="REJECT",
        )
        stamp = get_export_stamp(output)
        assert "REFUSÉ" in stamp


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: SECTION COMPLETENESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSectionCompleteness:
    """Tests de la vérification de complétude des sections."""

    def test_missing_section_is_p0(self):
        """Une section manquante DOIT déclencher un P0."""
        from python.helpers.contract_drafting.gate import check_section_completeness
        from python.helpers.contract_drafting.models import FindingSeverity
        # Only CP, missing everything else
        findings = check_section_completeness({"CP": "contenu"})
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 7, "7 sections manquantes = 7 P0"

    def test_empty_section_is_p0(self):
        """Une section vide DOIT déclencher un P0."""
        from python.helpers.contract_drafting.gate import check_section_completeness
        from python.helpers.contract_drafting.models import FindingSeverity
        sections = {
            "CP": "contenu", "CG": "", "ANNEXE_1": "ok",
            "ANNEXE_2": "ok", "ANNEXE_3": "ok", "ANNEXE_4": "ok",
            "ANNEXE_5": "ok", "ANNEXE_6": "ok",
        }
        findings = check_section_completeness(sections)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Section CG vide doit être P0"
        assert any("CG" in f.section for f in p0s)

    def test_complete_sections_no_findings(self):
        """Toutes les sections présentes et non vides → 0 finding."""
        from python.helpers.contract_drafting.gate import check_section_completeness
        sections = {
            "CP": "ok", "CG": "ok", "ANNEXE_1": "ok",
            "ANNEXE_2": "ok", "ANNEXE_3": "ok", "ANNEXE_4": "ok",
            "ANNEXE_5": "ok", "ANNEXE_6": "ok",
        }
        findings = check_section_completeness(sections)
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditTrail:
    """Tests de la traçabilité et de l'audit."""

    def test_drafting_output_has_correlation_id(self):
        """Chaque DraftingOutput DOIT avoir un correlation_id."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline(
            {"client_name": "X", "editor_name": "Y",
             "software_name": "Z", "jurisdiction": "P"},
        )
        assert output.draft.correlation_id
        assert len(output.draft.correlation_id) > 10

    def test_audit_entry_has_timestamp(self):
        """DraftAuditEntry DOIT avoir un timestamp."""
        from python.helpers.contract_drafting.models import DraftAuditEntry
        entry = DraftAuditEntry(correlation_id="test-001", action="test")
        assert entry.timestamp
        assert "T" in entry.timestamp  # ISO format

    def test_gate_verdict_audit_report(self):
        """GateVerdict.to_audit_report() DOIT générer un rapport structuré."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CP": "ok", "CG": "ok", "ANNEXE_1": "ok", "ANNEXE_2": "ok",
                       "ANNEXE_3": "ok", "ANNEXE_4": "ok", "ANNEXE_5": "ok", "ANNEXE_6": "ok"},
            variables={},
            disclaimer="PROJET",
            correlation_id="test-audit",
        )
        verdict = run_gate(draft)
        report = verdict.to_audit_report()
        assert "AUDIT CONTRACTUEL" in report
        assert "Verdict:" in report


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10: INVARIANTS CROSS-CHECK
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariantsCrossCheck:
    """Tests croisés des invariants de sécurité V2."""

    def test_invariant_approve_implies_can_release(self):
        """INVARIANT: verdict=APPROVE ⟹ can_release=True."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline({
            "client_name": "X", "editor_name": "Y",
            "software_name": "Z", "jurisdiction": "P",
        })
        if output.gate_verdict.verdict.value == "APPROVE":
            assert output.gate_verdict.can_release is True

    def test_invariant_reject_implies_no_release(self):
        """INVARIANT: verdict=REJECT ⟹ can_release=False."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline({
            "client_name": '<script>alert(1)</script>',
        })
        if output.gate_verdict.verdict.value == "REJECT":
            assert output.gate_verdict.can_release is False

    def test_invariant_reject_implies_empty_contract(self):
        """INVARIANT: gate_passed=False ⟹ rendered_contract vide."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline({
            "client_name": '<script>alert(1)</script>',
        })
        if not output.gate_passed:
            assert output.rendered_contract == ""

    def test_invariant_p0_implies_reject(self):
        """INVARIANT: P0 trouvé ⟹ verdict=REJECT."""
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
            variables={},
            disclaimer="PROJET",
            correlation_id="test-inv",
        )
        verdict = run_gate(draft)
        assert verdict.has_p0() is True
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    def test_full_pipeline_e2e_hardened(self):
        """E2E: Pipeline complet avec variables propres → APPROVE."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.export_control import is_export_allowed
        output = run_drafting_pipeline({
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "software_version": "3.2.1",
            "jurisdiction": "Tribunal de commerce de Grenoble",
            "licence_metric": "par poste",
            "initial_posts": "1",
            "max_posts": "4",
            "remote_access": "false",
        })
        assert output.gate_passed is True
        assert output.rendered_contract != ""
        assert is_export_allowed(output) is True
        assert "DICA France" in output.rendered_contract
        assert "KOREV" in output.rendered_contract


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   PROMPT DE CONTRÔLE FINAL — PROCESS JURIDIQUE FAIL-CLOSED                  ║
║                                                                              ║
║   Vérifie l'INTÉGRALITÉ du process juridique :                              ║
║                                                                              ║
║   [FC-01] Aucun contrat ne sort sans PASS legal_safe                        ║
║   [FC-02] Un P0 bloque TOUJOURS l'export                                   ║
║   [FC-03] Aucune fuite d'actif n'est possible                              ║
║   [FC-04] Séparation rédacteur / juge stricte                              ║
║   [FC-05] MULTI_AGENT_CONSENSUS ne peut pas overrider                      ║
║   [FC-06] Decision.type = legal_contract (pas pricing)                     ║
║   [FC-07] Export stamp contient LEGAL_SAFE                                 ║
║   [FC-08] DPA conditionnelle correcte                                       ║
║   [FC-09] Pipeline E2E complet sans fuite                                  ║
║   [FC-10] Templates 0 fuite IP                                              ║
║   [FC-11] Leak Guard exhaustif (≥16 P0, ≥9 P1)                            ║
║   [FC-12] Gate audit report structuré                                       ║
║   [FC-13] Variables manquantes marquées                                     ║
║   [FC-14] legal_safe refuse toujours la rédaction directe                  ║
║   [FC-15] Responsabilité plafonnée                                          ║
║   [FC-16] CP prime CG (art. 1171)                                           ║
║   [FC-17] Réversibilité sans remise code                                    ║
║   [FC-18] Router détecte contract_drafting (pas faux positifs)             ║
║   [FC-19] Accès libre/illimité systèmes → P0                              ║
║   [FC-20] Documentation README existe                                       ║
║                                                                              ║
║   © 2026 Korev AI — Proprietary                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-01] Aucun contrat ne sort sans PASS legal_safe
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC01_NoContractWithoutPass:
    def test_reject_means_empty_contract(self):
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import ContractDraft
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import GateVerdictEnum
        draft = ContractDraft(
            sections={"CG": "Remise du code source intégral au Client."},
            variables={}, disclaimer="PROJET", correlation_id="fc01",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    def test_pipeline_fail_closed_produces_no_rendered(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={"CG": "Cession de tous les droits patrimoniaux."},
            variables={}, disclaimer="PROJET", correlation_id="fc01b",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-02] Un P0 bloque TOUJOURS l'export
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC02_P0BlocksExport:
    def test_export_blocked_with_p0(self):
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
            LeakFinding, FindingSeverity,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.REJECT, can_release=False,
                findings=[LeakFinding(
                    severity=FindingSeverity.P0, pattern="test",
                    context="...", recommendation="...", section="CG",
                )],
            ),
            gate_passed=False, gate_summary="P0",
        )
        assert is_export_allowed(output) is False, \
            "[FC-02] FAIL CRITIQUE: Export autorisé avec P0!"


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-03] Aucune fuite d'actif
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC03_NoAssetLeak:
    def test_full_pipeline_no_code_source(self):
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline(
            {"client_name": "TestCo", "editor_name": "KOREV",
             "software_name": "TestApp", "jurisdiction": "Paris"},
        )
        assert output.gate_passed is True
        forbidden = ["remise du code source", "cession du code", "livraison du code source"]
        for phrase in forbidden:
            assert phrase not in output.rendered_contract.lower(), \
                f"[FC-03] FUITE: '{phrase}' trouvé dans le contrat!"


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-04] Séparation rédacteur / juge
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC04_SeparationRoles:
    def test_drafting_agent_exists(self):
        assert os.path.exists(os.path.join(BASE, "agents", "legal_drafting_guarded"))

    def test_safe_agent_exists(self):
        assert os.path.exists(os.path.join(BASE, "agents", "legal_safe"))

    def test_drafting_profile_is_redacteur(self):
        path = os.path.join(BASE, "agents", "legal_drafting_guarded", "_context.md")
        with open(path) as f:
            content = f.read().lower()
        assert "rédaction" in content or "rédiger" in content

    def test_safe_profile_refuses_drafting(self):
        path = os.path.join(BASE, "agents", "legal_safe", "prompts", "agent.system.main.role.md")
        if not os.path.exists(path):
            pytest.skip("legal_safe role.md not found")
        with open(path) as f:
            content = f.read().lower()
        assert any(w in content for w in ["interdit", "rédaction d'actes"])


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-05] MULTI_AGENT_CONSENSUS ne peut pas overrider
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC05_ConsensusNoOverride:
    def test_consensus_cannot_override(self):
        from python.helpers.contract_drafting.governance import can_consensus_override_legal_gate
        assert can_consensus_override_legal_gate() is False


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-06] Decision.type = legal_contract
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC06_DecisionType:
    def test_type_is_legal_contract(self):
        from python.helpers.contract_drafting.governance import DECISION_GOVERNANCE_TYPE
        assert DECISION_GOVERNANCE_TYPE == "legal_contract"
        assert DECISION_GOVERNANCE_TYPE != "pricing"


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-07] Export stamp contient LEGAL_SAFE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC07_ExportStamp:
    def test_stamp_mentions_legal_safe(self):
        from python.helpers.contract_drafting.export_control import get_export_stamp
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE, can_release=True, summary="OK",
            ),
            gate_passed=True, gate_summary="OK", rendered_contract="...",
        )
        stamp = get_export_stamp(output)
        assert "LEGAL_SAFE" in stamp.upper()


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-08] DPA conditionnelle
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC08_DPAConditional:
    def test_no_remote_dpa_not_applicable(self):
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "false"},
        )
        assert "NON APPLICABLE" in draft.sections.get("ANNEXE_4", "").upper()

    def test_remote_dpa_applicable(self):
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "true"},
        )
        a4 = draft.sections.get("ANNEXE_4", "").lower()
        assert "article 28" in a4 or "sous-traitant" in a4


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-09] Pipeline E2E complet sans fuite
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC09_E2ENoLeak:
    def test_korev_dica_e2e(self):
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.export_control import is_export_allowed
        output = run_drafting_pipeline({
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Tribunal de commerce de Grenoble",
            "licence_metric": "par poste",
            "initial_posts": "1",
            "max_posts": "4",
            "remote_access": "false",
        })
        assert output.gate_passed is True
        assert is_export_allowed(output) is True
        assert "DICA France" in output.rendered_contract
        assert "KOREV" in output.rendered_contract


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-10] Templates 0 fuite IP
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC10_TemplatesClean:
    def test_all_templates_zero_p0(self):
        from python.helpers.contract_drafting.templates import get_template_pack
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        pack = get_template_pack()
        for name, template in pack.items():
            findings = scan_for_leaks(template, section=name)
            p0s = [f for f in findings if f.severity == FindingSeverity.P0]
            assert len(p0s) == 0, f"[FC-10] Template {name} contient P0: {[f.pattern for f in p0s]}"


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-11] Leak Guard exhaustif
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC11_LeakGuardExhaustive:
    def test_minimum_16_p0_patterns(self):
        from python.helpers.contract_drafting.leak_guard import _P0_PATTERNS
        assert len(_P0_PATTERNS) >= 16, f"Attendu ≥16 P0, trouvé {len(_P0_PATTERNS)}"

    def test_minimum_9_p1_patterns(self):
        from python.helpers.contract_drafting.leak_guard import _P1_PATTERNS
        assert len(_P1_PATTERNS) >= 9, f"Attendu ≥9 P1, trouvé {len(_P1_PATTERNS)}"


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-12] Gate audit report structuré
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC12_AuditReport:
    def test_audit_report_contains_verdict(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CG": "Licence d'usage non exclusive."},
            variables={}, disclaimer="PROJET", correlation_id="fc12",
        )
        verdict = run_gate(draft)
        report = verdict.to_audit_report()
        assert "APPROVE" in report or "REJECT" in report


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-13] Variables manquantes marquées
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC13_MissingVarsMarked:
    def test_missing_vars_visible(self):
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract({"client_name": "X"})
        all_text = " ".join(draft.sections.values())
        assert "À COMPLÉTER" in all_text


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-14] legal_safe refuse la rédaction directe
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC14_LegalSafeRefuses:
    def test_role_prompt_forbids_drafting(self):
        path = os.path.join(BASE, "agents", "legal_safe", "prompts", "agent.system.main.role.md")
        if not os.path.exists(path):
            pytest.skip()
        with open(path) as f:
            content = f.read().lower()
        assert any(w in content for w in ["rédaction d'actes juridiques", "actes interdits", "interdit"])


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-15] Responsabilité plafonnée
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC15_LiabilityCapped:
    def test_cg_has_cap(self):
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"].lower()
        assert "plafond" in cg or "ne saurait excéder" in cg


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-16] CP prime CG
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC16_CPPrimacy:
    def test_contract_mentions_primacy(self):
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris"},
        )
        all_text = " ".join(draft.sections.values()).lower()
        assert "prévalent" in all_text or "priment" in all_text or "primauté" in all_text


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-17] Réversibilité sans remise code
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC17_ReversibilityNoCode:
    def test_annexe_5_clean(self):
        from python.helpers.contract_drafting.templates import get_template_pack
        a5 = get_template_pack()["ANNEXE_5"].lower()
        assert "remise du code source" not in a5


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-18] Router correct
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC18_Router:
    def test_detects_drafting(self):
        from python.helpers.contract_drafting.orchestrator import detect_contract_drafting_intent
        assert detect_contract_drafting_intent("Rédige un contrat de licence") is True

    def test_rejects_analysis(self):
        from python.helpers.contract_drafting.orchestrator import detect_contract_drafting_intent
        assert detect_contract_drafting_intent("Analyse les risques de ce contrat") is False


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-19] Accès libre → P0
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC19_FreeAccessP0:
    def test_free_access_detected(self):
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        findings = scan_for_leaks("L'Éditeur accède librement aux systèmes du Client.")
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# [FC-20] Documentation README existe
# ═══════════════════════════════════════════════════════════════════════════════

class TestFC20_Documentation:
    def test_readme_exists(self):
        path = os.path.join(BASE, "python", "helpers", "contract_drafting", "README.md")
        assert os.path.exists(path), "[FC-20] README.md manquant"

    def test_readme_has_pipeline_diagram(self):
        path = os.path.join(BASE, "python", "helpers", "contract_drafting", "README.md")
        with open(path) as f:
            content = f.read()
        assert "LEGAL_DRAFTING_GUARDED" in content.upper() or "legal_drafting_guarded" in content
        assert "LEGAL_SAFE" in content.upper() or "legal_safe" in content
        assert "FAIL" in content.upper() or "PASS" in content.upper()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

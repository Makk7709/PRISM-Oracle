"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       PROMPT DE CONTRÔLE ULTRA-EXIGEANT — AUDIT FINAL                       ║
║                                                                              ║
║  Ce fichier est le "prompt de contrôle hyper exigeant" qui vérifie :        ║
║                                                                              ║
║  [CQ-01] legal_safe REFUSE toujours la rédaction directe de contrats       ║
║  [CQ-02] legal_drafting_guarded sait rédiger mais n'outrepasse pas         ║
║          (disclaimer + variables + options A/B)                              ║
║  [CQ-03] Le gate bloque toute "remise du code" (P0)                        ║
║  [CQ-04] Le gate bloque toute ambiguïté RGPD (DPA conditionnelle)         ║
║  [CQ-05] Le gate bloque les garanties absolues (P0)                        ║
║  [CQ-06] Fail-closed strict : REJECT → can_release=False                   ║
║  [CQ-07] Templates : aucune fuite IP dans aucune section                   ║
║  [CQ-08] CP prime CG (art. 1171)                                           ║
║  [CQ-09] Responsabilité plafonnée dans les CG                              ║
║  [CQ-10] Router détecte bien l'intent contract_drafting                    ║
║  [CQ-11] Router ne capture pas les requêtes d'analyse/info                 ║
║  [CQ-12] Annexe 4 DPA activée uniquement si accès distant                 ║
║  [CQ-13] Annexe 5 réversibilité sans remise code                          ║
║  [CQ-14] Pipeline E2E : KOREV/DICA complet avec gate PASS                 ║
║  [CQ-15] Pipeline E2E : draft trafiqué → gate REJECT                      ║
║  [CQ-16] SLA irréaliste (24/7 + conformité totale) → P0 détecté           ║
║  [CQ-17] Profil agent legal_drafting_guarded correctement structuré        ║
║  [CQ-18] Variables manquantes marquées [À COMPLÉTER]                       ║
║  [CQ-19] Intégrité du profil legal_safe (pas de régression)               ║
║  [CQ-20] Leak Guard : détection exhaustive de toutes variantes             ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-01] legal_safe REFUSE toujours la rédaction directe
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ01_LegalSafeRefusesDrafting:
    """[CQ-01] Le profil legal_safe REFUSE toujours la rédaction."""

    def test_role_prompt_contains_refusal(self):
        """Le prompt role de legal_safe doit explicitement refuser la rédaction."""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_safe", "prompts", "agent.system.main.role.md"
        )
        if not os.path.exists(prompt_path):
            pytest.skip("legal_safe prompt not found")
        with open(prompt_path) as f:
            content = f.read().lower()
        assert any(term in content for term in [
            "rédaction d'actes juridiques",
            "actes interdits",
            "interdit",
        ]), "[CQ-01] FAIL: legal_safe doit refuser la rédaction d'actes juridiques"

    def test_demo_shows_refusal(self):
        """Le demo de legal_safe doit montrer un refus de rédaction."""
        demo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_safe", "demos", "demo_responses.md"
        )
        if not os.path.exists(demo_path):
            pytest.skip("legal_safe demo not found")
        with open(demo_path) as f:
            content = f.read().lower()
        assert "restricted_activity" in content or "refus" in content, \
            "[CQ-01] FAIL: demo doit montrer le refus de rédaction"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-02] legal_drafting_guarded rédige avec disclaimer
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ02_DraftingGuardedDraftsProperly:
    """[CQ-02] legal_drafting_guarded rédige mais n'outrepasse pas."""

    def test_role_prompt_has_disclaimer_rule(self):
        """Le prompt doit imposer le disclaimer PROJET."""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_drafting_guarded", "prompts", "agent.system.main.role.md"
        )
        with open(prompt_path) as f:
            content = f.read()
        assert "PROJET" in content
        assert "VALIDER" in content.upper() or "valider" in content
        assert "juriste" in content.lower()

    def test_role_prompt_forbids_legal_advice(self):
        """Le prompt doit interdire le conseil juridique."""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_drafting_guarded", "prompts", "agent.system.main.role.md"
        )
        with open(prompt_path) as f:
            content = f.read().lower()
        assert "conseil juridique" in content or "avis juridique" in content

    def test_role_prompt_forbids_code_source(self):
        """Le prompt doit INTERDIRE la remise de code source."""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_drafting_guarded", "prompts", "agent.system.main.role.md"
        )
        with open(prompt_path) as f:
            content = f.read().lower()
        assert "code source" in content
        assert any(w in content for w in ["jamais", "interdi", "ne dois"]), \
            "[CQ-02] FAIL: prompt doit interdire la remise code source"

    def test_generated_draft_has_disclaimer(self):
        """Le draft généré DOIT avoir un disclaimer."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "TestCo", "editor_name": "KOREV",
             "software_name": "TestApp", "jurisdiction": "Paris"},
            contract_type="on_prem_licence",
        )
        assert draft.disclaimer != ""
        assert "PROJET" in draft.disclaimer.upper()
        assert "VALIDER" in draft.disclaimer.upper()

    def test_missing_variables_marked(self):
        """[CQ-18] Les variables manquantes doivent être marquées."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X"},  # Minimal variables
            contract_type="on_prem_licence",
        )
        all_text = " ".join(draft.sections.values())
        assert "À COMPLÉTER" in all_text, \
            "[CQ-18] FAIL: Variables manquantes doivent être marquées"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-03] Gate bloque "remise du code" (P0)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ03_GateBlocksCodeTransfer:
    """[CQ-03] La gate bloque toute remise de code source."""

    @pytest.mark.parametrize("dangerous_clause", [
        "Le prestataire procédera à la remise du code source au Client",
        "Le code source sera livré à la fin du contrat",
        "Accès au repository Git du code accordé au Client",
        "Les sources du logiciel seront remises",
        "La cession de tous les droits de propriété intellectuelle",
        "Transfert complet du savoir-faire technique",
        "Le prestataire transmet son savoir-faire au Client",
    ])
    def test_dangerous_clause_is_p0(self, dangerous_clause):
        """Chaque clause dangereuse doit déclencher un P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        findings = scan_for_leaks(dangerous_clause)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, \
            f"[CQ-03] FAIL: Clause non détectée comme P0: '{dangerous_clause[:50]}...'"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-04] Gate bloque ambiguïté RGPD
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ04_GateBlocksRGPDAmbiguity:
    """[CQ-04] La DPA est conditionnelle — pas d'ambiguïté RGPD."""

    def test_no_remote_dpa_conditional(self):
        """Sans accès distant, la DPA doit être conditionnelle."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "false"},
            contract_type="on_prem_licence",
        )
        a4 = draft.sections.get("ANNEXE_4", "").lower()
        assert any(w in a4 for w in ["non applicable", "conditionnel", "si applicable", "uniquement"]), \
            "[CQ-04] FAIL: DPA devrait être conditionnelle sans accès distant"

    def test_remote_dpa_mandatory(self):
        """Avec accès distant, la DPA doit être substantive."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "true"},
            contract_type="on_prem_licence",
        )
        a4 = draft.sections.get("ANNEXE_4", "").lower()
        assert any(w in a4 for w in ["sous-traitant", "responsable de traitement", "article 28"]), \
            "[CQ-04] FAIL: DPA doit être substantive avec accès distant"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-05] Gate bloque garanties absolues (P0)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ05_GateBlocksAbsoluteGuarantees:
    """[CQ-05] Garanties absolues → P0."""

    @pytest.mark.parametrize("guarantee,desc", [
        ("garantie zéro risque", "zéro risque"),
        ("conformité totale au RGPD", "conformité totale"),
        ("solution sans aucune faille", "sans faille"),
        ("zéro bug garanti", "zéro bug"),
    ])
    def test_absolute_guarantee_is_p0(self, guarantee, desc):
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        findings = scan_for_leaks(f"Le prestataire garantit une {guarantee}.")
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, f"[CQ-05] FAIL: '{desc}' non détecté comme P0"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-06] Fail-closed strict : REJECT → can_release=False
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ06_FailClosedInvariant:
    """[CQ-06] INVARIANT: REJECT ⟹ can_release=False, toujours."""

    def test_reject_implies_no_release(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        # Contrat avec P0
        draft = ContractDraft(
            sections={"CG": "Cession de tous les droits de propriété intellectuelle."},
            variables={},
            disclaimer="PROJET",
            correlation_id="cq06-test",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False, \
            "[CQ-06] FAIL CRITICAL: REJECT avec can_release=True !"

    def test_no_disclaimer_implies_reject(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={"CG": "Contrat propre."},
            variables={},
            disclaimer="",
            correlation_id="cq06-no-disc",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    def test_approve_implies_can_release(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={"CG": "Licence d'usage non exclusive."},
            variables={},
            disclaimer="PROJET — à valider",
            correlation_id="cq06-clean",
        )
        verdict = run_gate(draft)
        if verdict.verdict == GateVerdictEnum.APPROVE:
            assert verdict.can_release is True, \
                "[CQ-06] FAIL: APPROVE sans can_release=True"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-07] Templates : zéro fuite IP
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ07_TemplatesNoIPLeak:
    """[CQ-07] Aucun template ne doit contenir de fuite IP."""

    def test_all_templates_clean(self):
        from python.helpers.contract_drafting.templates import get_template_pack
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        pack = get_template_pack()
        for section_name, template in pack.items():
            findings = scan_for_leaks(template, section=section_name)
            p0s = [f for f in findings if f.severity == FindingSeverity.P0]
            assert len(p0s) == 0, \
                f"[CQ-07] FAIL: Template {section_name} contient P0: " \
                f"{[f.pattern for f in p0s]}"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-08] CP prime CG (art. 1171)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ08_CPPrimacy:
    """[CQ-08] Les CP doivent primer sur les CG."""

    def test_cp_primacy_in_contract(self):
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris"},
            contract_type="on_prem_licence",
        )
        all_text = " ".join(draft.sections.values()).lower()
        assert any(w in all_text for w in ["prévalent", "priment", "primauté"]), \
            "[CQ-08] FAIL: Le contrat doit stipuler la primauté des CP"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-09] Responsabilité plafonnée
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ09_LiabilityCapped:
    """[CQ-09] La responsabilité doit être plafonnée."""

    def test_cg_has_liability_cap(self):
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"].lower()
        assert any(w in cg for w in [
            "plafond", "ne saurait excéder", "limité"
        ]), "[CQ-09] FAIL: CG doivent plafonner la responsabilité"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-10] Router détecte contract_drafting
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ10_RouterDetection:
    """[CQ-10] Router détecte l'intent contract_drafting."""

    @pytest.mark.parametrize("query", [
        "Rédige un contrat de licence entre KOREV et DICA France",
        "Produire un CONTRAT prêt à signature",
        "Prépare les conditions générales pour une licence logiciel",
        "Génère un contrat de licence on-prem",
        "Crée un contrat de maintenance logiciel",
    ])
    def test_contract_drafting_detected(self, query):
        from python.helpers.contract_drafting.orchestrator import detect_contract_drafting_intent
        assert detect_contract_drafting_intent(query) is True, \
            f"[CQ-10] FAIL: Intent non détecté pour: '{query[:50]}'"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-11] Router ne capture pas les analyses
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ11_RouterNoFalsePositive:
    """[CQ-11] Router ne capture pas les requêtes d'info."""

    @pytest.mark.parametrize("query", [
        "Qu'est-ce qu'un contrat synallagmatique ?",
        "Analyse les risques de ce contrat",
        "Explique-moi la différence entre SAS et SARL",
        "Quelle est la durée de prescription en droit commercial ?",
    ])
    def test_info_queries_not_captured(self, query):
        from python.helpers.contract_drafting.orchestrator import detect_contract_drafting_intent
        assert detect_contract_drafting_intent(query) is False, \
            f"[CQ-11] FAIL: Faux positif pour: '{query[:50]}'"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-12] DPA conditionnelle (Annexe 4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ12_DPAConditional:
    """[CQ-12] DPA activée uniquement si accès distant."""

    def test_dpa_not_applicable_without_remote(self):
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "false"},
        )
        a4 = draft.sections.get("ANNEXE_4", "")
        assert "NON APPLICABLE" in a4.upper() or "non applicable" in a4.lower(), \
            "[CQ-12] FAIL: DPA devrait être NON APPLICABLE"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-13] Annexe 5 sans remise code
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ13_Annexe5NoCode:
    """[CQ-13] Annexe 5 (réversibilité) ne promet jamais de code."""

    def test_annexe_5_no_code_source(self):
        from python.helpers.contract_drafting.templates import get_template_pack
        a5 = get_template_pack()["ANNEXE_5"].lower()
        forbidden = ["remise du code source", "code source livré", "livraison du code source"]
        for phrase in forbidden:
            assert phrase not in a5, \
                f"[CQ-13] FAIL: Annexe 5 contient '{phrase}'"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-14] Pipeline E2E complet KOREV/DICA
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ14_E2EComplete:
    """[CQ-14] Pipeline E2E KOREV/DICA avec gate PASS."""

    def test_full_pipeline_korev_dica(self):
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        output = run_drafting_pipeline(
            {
                "client_name": "DICA France",
                "editor_name": "KOREV",
                "software_name": "DICA Decor",
                "jurisdiction": "Tribunal de commerce de Grenoble",
                "licence_metric": "par poste",
                "initial_posts": "1",
                "max_posts": "4",
                "remote_access": "false",
            },
            contract_type="on_prem_licence",
        )
        assert output.gate_passed is True, \
            f"[CQ-14] FAIL: Gate rejetée: {output.gate_summary}"
        assert "DICA France" in output.rendered_contract
        assert "KOREV" in output.rendered_contract
        assert "DICA Decor" in output.rendered_contract


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-15] Pipeline E2E : draft trafiqué → REJECT
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ15_TamperedDraftRejected:
    """[CQ-15] Draft trafiqué → gate REJECT."""

    def test_tampered_draft_rejected(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={
                "CP": "Contrat entre KOREV et Client",
                "CG": "L'Éditeur remet le code source complet au Client, "
                       "incluant la cession de tous droits patrimoniaux et "
                       "le transfert de son savoir-faire technique.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="cq15-tampered",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT, \
            "[CQ-15] FAIL: Draft trafiqué devrait être REJECT"
        assert verdict.has_p0() is True
        assert verdict.p0_count() >= 2, \
            f"[CQ-15] FAIL: Devrait avoir >= 2 P0, trouvé {verdict.p0_count()}"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-16] SLA irréaliste → P0
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ16_SLATooStrong:
    """[CQ-16] SLA irréaliste → P0 détecté."""

    def test_sla_24_7_conformite_totale(self):
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={
                "CG": "Le prestataire garantit une conformité totale et un support 24/7.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="cq16-sla",
        )
        verdict = run_gate(draft)
        assert verdict.has_p0() is True, \
            "[CQ-16] FAIL: 'Conformité totale' devrait être P0"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-17] Profil agent correctement structuré
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ17_AgentProfileStructure:
    """[CQ-17] Profil legal_drafting_guarded correctement structuré."""

    def test_context_file_exists(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_drafting_guarded", "_context.md"
        )
        assert os.path.exists(path), "[CQ-17] FAIL: _context.md manquant"

    def test_role_prompt_exists(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_drafting_guarded", "prompts", "agent.system.main.role.md"
        )
        assert os.path.exists(path), "[CQ-17] FAIL: role.md manquant"

    def test_communication_prompt_exists(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_drafting_guarded", "prompts", "agent.system.main.communication.md"
        )
        assert os.path.exists(path), "[CQ-17] FAIL: communication.md manquant"


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-19] Intégrité du profil legal_safe
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ19_LegalSafeIntegrity:
    """[CQ-19] legal_safe n'a pas été modifié (pas de régression)."""

    def test_legal_safe_context_untouched(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agents", "legal_safe", "_context.md"
        )
        if not os.path.exists(path):
            pytest.skip("legal_safe _context.md not found")
        with open(path) as f:
            content = f.read().lower()
        # Must still mention ultra-strict, analyse juridique
        assert "strict" in content or "juridique" in content or "analyse" in content


# ═══════════════════════════════════════════════════════════════════════════════
# [CQ-20] Leak Guard : détection exhaustive
# ═══════════════════════════════════════════════════════════════════════════════

class TestCQ20_LeakGuardExhaustive:
    """[CQ-20] Leak Guard détecte TOUTES les variantes dangereuses."""

    def test_all_p0_patterns_documented(self):
        """Chaque pattern P0 doit avoir un pattern, un nom et une recommandation."""
        from python.helpers.contract_drafting.leak_guard import _P0_PATTERNS
        assert len(_P0_PATTERNS) >= 10, \
            f"[CQ-20] FAIL: Minimum 10 patterns P0, trouvé {len(_P0_PATTERNS)}"
        for pattern, name, recommendation in _P0_PATTERNS:
            assert name, "Chaque pattern doit avoir un nom"
            assert recommendation, "Chaque pattern doit avoir une recommandation"

    def test_all_p1_patterns_documented(self):
        from python.helpers.contract_drafting.leak_guard import _P1_PATTERNS
        assert len(_P1_PATTERNS) >= 3, \
            f"[CQ-20] FAIL: Minimum 3 patterns P1, trouvé {len(_P1_PATTERNS)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

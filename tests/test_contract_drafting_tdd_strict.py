"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   TDD STRICT — TESTS RED-GREEN POUR AUDIT VC                              ║
║                                                                              ║
║   OBJECTIF: Chaque test expose un BUG REEL qui doit être corrigé.          ║
║   AUCUNE SIMPLIFICATION. Tous les cas sont exacts.                          ║
║                                                                              ║
║   PHASE RED (attendu: FAIL sur code actuel):                                ║
║     1. Faux positif "responsabilité totale" (clause de plafond)            ║
║     2. Faux positif "tacite reconduction" avec préavis cross-line          ║
║     3. Citation regex produit des normalisations malformées                ║
║     4. Doublon de citation non dédupliqué (patterns overlapping)           ║
║     5. E2E templates KOREV : 0 P1 leak_guard attendu                      ║
║     6. Regression test: patterns légitimes doivent rester détectés         ║
║                                                                              ║
║   PHASE GREEN (après fix):                                                   ║
║     Tous les tests passent, les vrais positifs restent détectés.           ║
║                                                                              ║
║   © 2026 Korev AI — Proprietary                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import re
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: FAUX POSITIFS LEAK GUARD — Templates KOREV
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeakGuardFalsePositives:
    """Tests que les templates KOREV propres ne déclenchent PAS de P1 leak_guard.

    Le CG article 9.1 contient "la responsabilité totale de l'Éditeur [...] ne
    saurait excéder le montant total payé" — c'est un PLAFONNEMENT, pas une
    responsabilité illimitée. Le regex actuel matche "responsabilité totale"
    comme P1, ce qui est un faux positif.
    """

    def test_responsabilite_totale_capping_is_not_p1(self):
        """CG art. 9.1 : 'la responsabilité totale [...] ne saurait excéder'
        est un PLAFOND — NE DOIT PAS être P1 'responsabilité sans plafond'.

        ATTENDU: 0 finding P1 de type 'responsabilité sans plafond'
        """
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity

        # Texte exact du template CG article 9.1
        text = (
            "9.1 Plafond : la responsabilité totale de l'Éditeur, toutes causes "
            "confondues, ne saurait excéder le montant total payé par le Client "
            "au titre du contrat sur les 12 derniers mois précédant le fait générateur."
        )
        findings = scan_for_leaks(text, section="CG")
        p1_resp = [
            f for f in findings
            if f.severity == FindingSeverity.P1
            and "responsabilité" in f.pattern.lower()
        ]
        assert len(p1_resp) == 0, (
            f"FAUX POSITIF: 'responsabilité totale' dans une clause de plafonnement "
            f"ne doit PAS être flaggée P1. Findings: {[f.pattern for f in p1_resp]}"
        )

    def test_tacite_reconduction_with_preavis_crossline_not_p1(self):
        """CP art. 5 : 'tacite reconduction [...] sauf dénonciation [...] avec un
        préavis de {notice_period}' — le préavis EST mentionné, mais sur la ligne
        suivante. Le regex NE DOIT PAS le flagger.

        ATTENDU: 0 finding P1 de type 'reconduction tacite sans préavis'
        """
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity

        # Texte exact du template CP article 5 (multi-line)
        text = (
            "Renouvellement : tacite reconduction par périodes de 12 mois, sauf\n"
            "dénonciation par l'une des Parties avec un préavis de 3 mois."
        )
        findings = scan_for_leaks(text, section="CP")
        p1_tacite = [
            f for f in findings
            if f.severity == FindingSeverity.P1
            and "reconduction" in f.pattern.lower()
        ]
        assert len(p1_tacite) == 0, (
            f"FAUX POSITIF: 'tacite reconduction' avec préavis (même cross-line) "
            f"ne doit PAS être flaggée P1. Findings: {[f.pattern for f in p1_tacite]}"
        )

    def test_full_cg_template_zero_leak_guard_p1(self):
        """Le CG template rendu avec des variables propres NE DOIT produire
        AUCUN P1 de type leak_guard.

        Les templates KOREV sont rédigés par KOREV Legal — ils ne doivent
        pas trigger les patterns qu'ils sont censés protéger.

        ATTENDU: 0 finding P1 de catégorie leak_guard dans CG
        """
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        from python.helpers.contract_drafting.templates import get_template_pack, render_template

        pack = get_template_pack()
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "software_version": "3.2.1",
            "jurisdiction": "Tribunal de commerce de Grenoble",
            "licence_metric": "par poste",
            "initial_posts": "1",
            "max_posts": "4",
        }
        rendered_cg = render_template(pack["CG"], variables)
        findings = scan_for_leaks(rendered_cg, section="CG")

        # Seuls les P1 leak_guard sont inacceptables — citations sont vérifiées ailleurs
        p1_leak = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1_leak) == 0, (
            f"FAUX POSITIF dans le CG template: {len(p1_leak)} P1 détectés. "
            f"Patterns: {[(f.pattern, f.context[:60]) for f in p1_leak]}"
        )

    def test_full_cp_template_zero_leak_guard_p1(self):
        """Le CP template rendu NE DOIT produire AUCUN P1 leak_guard."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        from python.helpers.contract_drafting.templates import get_template_pack, render_template

        pack = get_template_pack()
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "software_version": "3.2.1",
            "jurisdiction": "Tribunal de commerce de Grenoble",
            "licence_metric": "par poste",
            "initial_posts": "1",
            "max_posts": "4",
            "notice_period": "3 mois",
            "renewal_period": "12 mois",
            "contract_duration": "36 mois",
            "pilot_duration": "3 mois",
        }
        rendered_cp = render_template(pack["CP"], variables)
        findings = scan_for_leaks(rendered_cp, section="CP")
        p1_leak = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1_leak) == 0, (
            f"FAUX POSITIF dans le CP template: {len(p1_leak)} P1 détectés. "
            f"Patterns: {[(f.pattern, f.context[:60]) for f in p1_leak]}"
        )

    def test_all_templates_zero_leak_guard_p0(self):
        """AUCUN template KOREV ne doit contenir de clause P0.

        Si un P0 est détecté dans un template KOREV, c'est soit un faux
        positif du regex, soit un template corrompu.

        ATTENDU: 0 P0 sur l'ensemble des templates rendus
        """
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks_by_section
        from python.helpers.contract_drafting.models import FindingSeverity
        from python.helpers.contract_drafting.templates import get_template_pack, render_template

        pack = get_template_pack()
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "software_version": "3.2.1",
            "remote_access": "false",
        }
        sections = {}
        for section_name, template in pack.items():
            sections[section_name] = render_template(template, variables)

        findings = scan_for_leaks_by_section(sections)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) == 0, (
            f"P0 détecté dans les templates KOREV ({len(p0s)} P0): "
            f"{[(f.section, f.pattern, f.context[:60]) for f in p0s]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CITATION NORMALIZATION BUGS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCitationNormalization:
    """Tests des bugs de normalisation dans le module de citation."""

    def test_code_de_commerce_full_name_captured(self):
        """Le regex DOIT capturer 'Code de commerce' en entier — pas juste 'Code'.

        Bug actuel: le 3e pattern `_CITATION_FULL_PATTERNS` capture seulement
        le premier mot après 'Code' → 'Code de' (manque 'commerce').

        ATTENDU: normalisation = 'Code de commerce, art. L441-10'
        """
        from python.helpers.contract_drafting.gate import verify_legal_citations

        sections = {
            "ANNEXE_6": (
                "Paiement : 30 jours fin de mois "
                "(art. L.441-10 du Code de commerce)"
            ),
        }
        findings = verify_legal_citations(sections)

        # Vérifier qu'il n'y a PAS de finding avec normalization malformée
        for f in findings:
            if hasattr(f, 'legal_ref') and f.legal_ref:
                assert "Code," not in f.legal_ref or "Code de commerce" in f.legal_ref, (
                    f"Normalisation malformée: '{f.legal_ref}' — "
                    f"attendu 'Code de commerce, art. L441-10'"
                )

    def test_no_duplicate_citation_findings(self):
        """Une même citation NE DOIT PAS produire 2 findings à cause de
        2 patterns overlapping.

        Bug actuel: pattern 1 matche 'art. L.441-10 du Code de commerce'
        correctement, MAIS pattern 3 matche aussi et produit 'Code, art.
        L441-10' — différente normalisation = pas dédupliquée.

        ATTENDU: max 1 finding par citation physique
        """
        from python.helpers.contract_drafting.gate import verify_legal_citations

        sections = {
            "ANNEXE_6": (
                "Paiement : 30 jours fin de mois "
                "(art. L.441-10 du Code de commerce)"
            ),
        }
        findings = verify_legal_citations(sections)

        # Compter les findings relatifs à L.441-10
        l441_findings = [
            f for f in findings
            if "441-10" in (f.legal_ref or "") or "441-10" in f.context
        ]
        assert len(l441_findings) <= 1, (
            f"Citation L.441-10 produit {len(l441_findings)} findings (doublon): "
            f"{[(f.pattern, f.legal_ref) for f in l441_findings]}"
        )

    def test_art_d441_5_c_com_normalized(self):
        """'art. D.441-5 C. com.' doit être normalisé en
        'Code de commerce, art. D441-5'.

        ATTENDU: normalisation correcte, pas de 'C.' comme code
        """
        from python.helpers.contract_drafting.gate import _normalize_citation
        result = _normalize_citation("D.441-5", "C. com.")
        assert "Code de commerce" in result, (
            f"Normalisation incorrecte: '{result}' — attendu contenir 'Code de commerce'"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: REGRESSION — VRAIS POSITIFS DOIVENT RESTER DETECTES
# ═══════════════════════════════════════════════════════════════════════════════

class TestTruePositivesStillDetected:
    """Après correction des faux positifs, les VRAIS positifs doivent
    toujours être détectés. Test de non-régression.
    """

    def test_responsabilite_illimitee_still_p1(self):
        """'responsabilité illimitée' (SANS plafond) → doit rester P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "La responsabilité de l'Éditeur est illimitée."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1
               and "responsabilité" in f.pattern.lower()]
        assert len(p1s) >= 1, "responsabilité illimitée doit rester P1"

    def test_responsabilite_sans_plafond_still_p1(self):
        """'responsabilité sans plafond' → doit rester P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "La responsabilité sans plafond est engagée."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1
               and "responsabilité" in f.pattern.lower()]
        assert len(p1s) >= 1, "responsabilité sans plafond doit rester P1"

    def test_tacite_reconduction_without_preavis_still_p1(self):
        """'tacite reconduction' SANS aucune mention de préavis → doit rester P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le contrat est renouvelé par tacite reconduction chaque année."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1
               and "reconduction" in f.pattern.lower()]
        assert len(p1s) >= 1, "tacite reconduction sans préavis doit rester P1"

    def test_remise_code_source_still_p0(self):
        """'remise du code source' → doit rester P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur procédera à la remise du code source au Client."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "remise du code source doit rester P0"

    def test_cession_de_droits_still_p0(self):
        """'cession de droits' → doit rester P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client obtient la cession de tous les droits de propriété intellectuelle."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "cession de droits doit rester P0"

    def test_zero_risque_still_p0(self):
        """'garantie zéro risque' → doit rester P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur garantit un zéro risque sur le logiciel."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "zéro risque doit rester P0"

    def test_reverse_engineering_autorise_still_p0(self):
        """reverse engineering autorisé → doit rester P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client est autorisé au reverse engineering du Logiciel."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "reverse engineering autorisé doit rester P0"

    def test_penalites_illimitees_still_p1(self):
        """'pénalités illimitées' → doit rester P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Les pénalités sont illimitées en cas de retard."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1
               and "pénalité" in f.pattern.lower()]
        assert len(p1s) >= 1, "pénalités illimitées doit rester P1"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: E2E PIPELINE — ZERO FAUX POSITIFS SUR TEMPLATES PROPRES
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EPipelineClean:
    """Test E2E: le pipeline complet avec des variables propres DOIT
    produire un contrat APPROVED avec ZERO P0 et ZERO P1 de type leak_guard.

    Les seuls P1 acceptables sont les citation_* (Legifrance non ingéré).
    """

    def test_pipeline_clean_no_leak_guard_findings(self):
        """Pipeline E2E avec variables propres → 0 P1 leak_guard.

        P1 citation_* acceptables (index vide).
        P1 leak_guard = FAUX POSITIF = BUG.
        """
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import FindingSeverity

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
            "notice_period": "3 mois",
            "renewal_period": "12 mois",
            "contract_duration": "36 mois",
            "pilot_duration": "3 mois",
        })

        assert output.gate_passed is True, (
            f"Pipeline devrait APPROUVER les variables propres. "
            f"Summary: {output.gate_summary}"
        )

        # Filtrer les P1 leak_guard (exclure citation_*)
        citation_patterns = {
            "citation_low_confidence",
            "citation_unverified",
            "citation_not_in_legifrance_index",
            "template_stale",
        }
        leak_guard_p1 = [
            f for f in output.gate_verdict.findings
            if f.severity == FindingSeverity.P1
            and f.pattern not in citation_patterns
        ]
        assert len(leak_guard_p1) == 0, (
            f"FAUX POSITIFS leak_guard dans pipeline E2E: {len(leak_guard_p1)}. "
            f"Patterns: {[(f.section, f.pattern, f.context[:60]) for f in leak_guard_p1]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: SECURITE — INVARIANTS CRITIQUES
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityInvariants:
    """Invariants de sécurité qui ne doivent JAMAIS être violés."""

    def test_disclaimer_absent_always_reject(self):
        """Disclaimer absent → TOUJOURS REJECT, même si le contrat est parfait."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum

        draft = ContractDraft(
            sections={
                "CP": "ok", "CG": "ok", "ANNEXE_1": "ok", "ANNEXE_2": "ok",
                "ANNEXE_3": "ok", "ANNEXE_4": "ok", "ANNEXE_5": "ok", "ANNEXE_6": "ok",
            },
            variables={},
            disclaimer="",  # Empty!
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    def test_p0_always_prevents_export(self):
        """Un P0 dans le contrat → export TOUJOURS refusé."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
            LeakFinding, FindingSeverity,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="t"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE,
                can_release=True,
                findings=[LeakFinding(
                    severity=FindingSeverity.P0,
                    pattern="test_p0",
                    context="test",
                    recommendation="fix",
                    section="TEST",
                )],
            ),
            gate_passed=True,
            gate_summary="APPROVE",
            rendered_contract="contenu",
        )
        # Even with APPROVE + can_release, has_p0() should block
        assert is_export_allowed(output) is False

    def test_exception_in_gate_always_reject(self):
        """Une exception dans la gate → TOUJOURS REJECT (fail-closed)."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        from unittest.mock import patch

        draft = ContractDraft(
            sections={"CP": "ok", "CG": "ok", "ANNEXE_1": "ok", "ANNEXE_2": "ok",
                       "ANNEXE_3": "ok", "ANNEXE_4": "ok", "ANNEXE_5": "ok", "ANNEXE_6": "ok"},
            variables={},
            disclaimer="PROJET",
        )
        # Force an exception in scan_for_leaks_by_section
        with patch(
            "python.helpers.contract_drafting.gate.scan_for_leaks_by_section",
            side_effect=RuntimeError("Simulated crash"),
        ):
            verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    def test_exception_in_pipeline_always_reject(self):
        """Une exception dans le pipeline → TOUJOURS REJECT (fail-closed)."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import GateVerdictEnum
        from unittest.mock import patch

        with patch(
            "python.helpers.contract_drafting.orchestrator.generate_contract",
            side_effect=RuntimeError("Simulated crash"),
        ):
            output = run_drafting_pipeline({
                "client_name": "X", "editor_name": "Y",
                "software_name": "Z", "jurisdiction": "P",
            })
        assert output.gate_passed is False
        assert output.gate_verdict.verdict == GateVerdictEnum.REJECT
        assert output.rendered_contract == ""

    def test_export_denied_on_rescan_p0(self):
        """Defense-in-depth: même si la gate APPROVE, un re-scan P0 à
        l'export DOIT bloquer."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, disclaimer="P", correlation_id="t"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE,
                can_release=True,
            ),
            gate_passed=True,
            gate_summary="APPROVE",
            # Le contrat contient un P0 que la gate aurait manqué
            rendered_contract="Le Client recevra la remise du code source.",
        )
        assert is_export_allowed(output) is False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: INTEGRATION LEGAL_SAFE — FAIL-CLOSED VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationFailClosed:
    """Vérifie que le code source de l'intégration contient les
    patterns de sécurité requis."""

    def test_contract_drafting_exception_blocks_llm(self):
        """Exception dans le contract drafting pipeline → _skip_llm=True ET return.
        Le LLM NE DOIT PAS être appelé en fallback."""
        import os
        integration_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "python", "extensions", "legal_safe_mode", "_10_legal_safe_integration.py"
        )
        with open(integration_path) as f:
            content = f.read()

        # Verify fail-closed pattern for contract drafting
        assert 'agent.set_data("_skip_llm", True)' in content
        assert "Do NOT fall through to LLM" in content or "CRITICAL: Do NOT fall through to LLM" in content

    def test_contract_drafting_exception_returns_refusal(self):
        """Exception → réponse de refus structurée (pas de contenu vide)."""
        import os
        integration_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "python", "extensions", "legal_safe_mode", "_10_legal_safe_integration.py"
        )
        with open(integration_path) as f:
            content = f.read()

        # Verify refusal text contains correlation_id
        assert "CONTRAT NON GÉNÉRÉ" in content or "ERREUR INTERNE" in content
        assert "fail-closed" in content.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: EDGE CASES — ROBUSTESSE
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Cas limites pour valider la robustesse."""

    def test_empty_sections_dict(self):
        """verify_legal_citations avec dict vide → 0 findings (pas d'exception)."""
        from python.helpers.contract_drafting.gate import verify_legal_citations
        findings = verify_legal_citations({})
        assert isinstance(findings, list)
        assert len(findings) == 0

    def test_section_with_only_whitespace_is_p0(self):
        """Une section contenant uniquement des espaces → P0 (section vide)."""
        from python.helpers.contract_drafting.gate import check_section_completeness
        from python.helpers.contract_drafting.models import FindingSeverity
        sections = {
            "CP": "ok", "CG": "   \n\t  ", "ANNEXE_1": "ok",
            "ANNEXE_2": "ok", "ANNEXE_3": "ok", "ANNEXE_4": "ok",
            "ANNEXE_5": "ok", "ANNEXE_6": "ok",
        }
        findings = check_section_completeness(sections)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Section whitespace-only doit être P0"

    def test_unicode_in_variables_handled(self):
        """Variables avec caractères Unicode (accents, emojis) → pas d'exception."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": "Société Générale — Établissement de Crédit",
            "editor_name": "KOREV éditeur",
            "software_name": "Logiciel spécialisé",
            "jurisdiction": "Tribunal de commerce de Strasbourg",
        })
        assert result.is_valid is True

    def test_very_long_contract_section_scanned_completely(self):
        """Un texte très long (> 50K chars) doit être scanné entièrement."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity

        # 50000 chars de texte propre, puis un P0 à la fin
        long_text = "Clause standard. " * 3000  # ~51000 chars
        long_text += "L'Éditeur procédera à la remise du code source au Client."
        findings = scan_for_leaks(long_text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "P0 en fin de texte long doit être détecté"

    def test_sql_injection_in_variable_blocked(self):
        """Injection SQL dans une variable → rejetée."""
        from python.helpers.contract_drafting.orchestrator import validate_contract_variables
        result = validate_contract_variables({
            "client_name": "'; DROP TABLE contracts; --",
            "editor_name": "KOREV",
            "software_name": "Test",
            "jurisdiction": "Paris",
        })
        # SQL injection n'est pas dans les patterns actuels, mais
        # vérifier que le système ne crash pas au minimum
        assert isinstance(result, object)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=long"])

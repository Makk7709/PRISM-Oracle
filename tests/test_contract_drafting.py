"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             CONTRACT DRAFTING GUARDED — TESTS TDD STRICT                    ║
║                                                                              ║
║  Tests écrits AVANT le code (TDD strict).                                   ║
║  Couvre:                                                                     ║
║    1. Models (dataclasses, enums, validation)                               ║
║    2. Templates (CP, CG, 6 Annexes, variables, structure)                   ║
║    3. Leak Guard (détection clauses dangereuses, P0 obligatoire)            ║
║    4. Gate (audit fail-closed, P0/P1/P2, verdict approve/reject)            ║
║    5. Orchestrator (pipeline Draft → Gate → Output)                         ║
║    6. Router (intent contract_drafting → legal_drafting_guarded)            ║
║    7. Invariants de sécurité (zéro fuite, RGPD conditionnelle)             ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import re
from typing import Dict, List, Any


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class TestContractModels:
    """Tests des dataclasses et enums du module contract_drafting."""

    def test_severity_enum_has_p0_p1_p2(self):
        """Les sévérités P0, P1, P2 doivent exister."""
        from python.helpers.contract_drafting.models import FindingSeverity
        assert hasattr(FindingSeverity, "P0")
        assert hasattr(FindingSeverity, "P1")
        assert hasattr(FindingSeverity, "P2")

    def test_gate_verdict_enum_has_approve_reject(self):
        """Le verdict de gate doit avoir APPROVE et REJECT."""
        from python.helpers.contract_drafting.models import GateVerdictEnum
        assert hasattr(GateVerdictEnum, "APPROVE")
        assert hasattr(GateVerdictEnum, "REJECT")

    def test_contract_section_enum_covers_all_parts(self):
        """Les sections doivent couvrir CP, CG, et les 6 Annexes."""
        from python.helpers.contract_drafting.models import ContractSection
        required = {"CP", "CG", "ANNEXE_1", "ANNEXE_2", "ANNEXE_3", "ANNEXE_4", "ANNEXE_5", "ANNEXE_6"}
        actual = {s.name for s in ContractSection}
        assert required.issubset(actual), f"Missing sections: {required - actual}"

    def test_leak_finding_dataclass_fields(self):
        """LeakFinding doit avoir severity, pattern, context, recommendation."""
        from python.helpers.contract_drafting.models import LeakFinding, FindingSeverity
        finding = LeakFinding(
            severity=FindingSeverity.P0,
            pattern="remise du code",
            context="Article 12.3: Le prestataire s'engage à la remise du code source",
            recommendation="Supprimer la remise du code source — remplacer par licence d'usage",
            section="CG",
        )
        assert finding.severity == FindingSeverity.P0
        assert "remise du code" in finding.pattern
        assert finding.section == "CG"

    def test_contract_draft_dataclass(self):
        """ContractDraft doit contenir sections, variables, metadata."""
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CP": "...", "CG": "..."},
            variables={"client_name": "DICA France"},
            disclaimer="PROJET — à valider par un juriste",
            correlation_id="test-001",
        )
        assert "CP" in draft.sections
        assert draft.disclaimer is not None
        assert draft.correlation_id == "test-001"

    def test_gate_verdict_dataclass(self):
        """GateVerdict doit contenir verdict, findings, can_release."""
        from python.helpers.contract_drafting.models import (
            GateVerdict, GateVerdictEnum, LeakFinding, FindingSeverity,
        )
        verdict = GateVerdict(
            verdict=GateVerdictEnum.REJECT,
            findings=[
                LeakFinding(
                    severity=FindingSeverity.P0,
                    pattern="code source",
                    context="...",
                    recommendation="...",
                    section="CG",
                )
            ],
            can_release=False,
            summary="P0 trouvé: remise de code source",
        )
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert not verdict.can_release
        assert len(verdict.findings) == 1

    def test_gate_verdict_p0_implies_reject(self):
        """Un GateVerdict avec P0 DOIT avoir can_release=False."""
        from python.helpers.contract_drafting.models import (
            GateVerdict, GateVerdictEnum, LeakFinding, FindingSeverity,
        )
        # This should be enforced by the model itself
        verdict = GateVerdict(
            verdict=GateVerdictEnum.REJECT,
            findings=[
                LeakFinding(
                    severity=FindingSeverity.P0,
                    pattern="test",
                    context="test",
                    recommendation="test",
                    section="CG",
                )
            ],
            can_release=False,
            summary="P0 found",
        )
        assert verdict.has_p0() is True
        assert verdict.can_release is False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

class TestContractTemplates:
    """Tests des templates contractuels."""

    def test_template_pack_exists(self):
        """Le template pack doit exister avec toutes les sections."""
        from python.helpers.contract_drafting.templates import get_template_pack
        pack = get_template_pack()
        required = {"CP", "CG", "ANNEXE_1", "ANNEXE_2", "ANNEXE_3", "ANNEXE_4", "ANNEXE_5", "ANNEXE_6"}
        assert required.issubset(set(pack.keys())), f"Missing: {required - set(pack.keys())}"

    def test_cp_template_has_required_sections(self):
        """Le template CP doit contenir les sections critiques."""
        from python.helpers.contract_drafting.templates import get_template_pack
        cp = get_template_pack()["CP"]
        # Vérifier que les sections essentielles sont présentes
        assert "{client_name}" in cp, "CP doit avoir la variable client_name"
        assert "{editor_name}" in cp, "CP doit avoir la variable editor_name"
        assert "{software_name}" in cp, "CP doit avoir la variable software_name"
        assert "{jurisdiction}" in cp, "CP doit avoir la variable jurisdiction"

    def test_cg_template_has_ip_clause(self):
        """Les CG doivent contenir une clause de propriété intellectuelle."""
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"]
        cg_lower = cg.lower()
        assert "propriété intellectuelle" in cg_lower or "propriété" in cg_lower, \
            "CG doit contenir une clause de propriété intellectuelle"

    def test_cg_template_has_no_code_source_transfer(self):
        """Les CG NE DOIVENT PAS contenir de transfert de code source."""
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"]
        cg_lower = cg.lower()
        forbidden = ["remise du code source", "cession du code", "transfert du code source"]
        for phrase in forbidden:
            assert phrase not in cg_lower, \
                f"CG contient une clause dangereuse: '{phrase}'"

    def test_cg_template_has_liability_cap(self):
        """Les CG doivent plafonner la responsabilité."""
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"]
        cg_lower = cg.lower()
        assert "plafond" in cg_lower or "responsabilité" in cg_lower, \
            "CG doit contenir un plafond de responsabilité"

    def test_cg_template_mentions_1170_1171(self):
        """Les CG doivent respecter les articles 1170/1171 du Code civil."""
        from python.helpers.contract_drafting.templates import get_template_pack
        cg = get_template_pack()["CG"]
        # Au minimum, la primauté des CP sur CG (art. 1171)
        assert "conditions particulières" in cg.lower() or "cp" in cg.lower(), \
            "CG doit mentionner la primauté des CP (art. 1171)"

    def test_annexe_1_describes_software(self):
        """Annexe 1 doit décrire le logiciel et ses modules."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a1 = get_template_pack()["ANNEXE_1"]
        assert "{software_name}" in a1, "Annexe 1 doit nommer le logiciel"

    def test_annexe_2_sla_has_p1_p2_p3(self):
        """Annexe 2 (SLA) doit définir les niveaux P1, P2, P3."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a2 = get_template_pack()["ANNEXE_2"]
        a2_lower = a2.lower()
        assert "p1" in a2_lower or "priorité 1" in a2_lower or "critique" in a2_lower, \
            "Annexe 2 doit définir le niveau P1 (critique)"
        assert "p2" in a2_lower or "priorité 2" in a2_lower, \
            "Annexe 2 doit définir le niveau P2"
        assert "p3" in a2_lower or "priorité 3" in a2_lower, \
            "Annexe 2 doit définir le niveau P3"

    def test_annexe_3_security_has_access_controls(self):
        """Annexe 3 (sécurité) doit encadrer les accès support."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a3 = get_template_pack()["ANNEXE_3"]
        a3_lower = a3.lower()
        assert "accès" in a3_lower or "access" in a3_lower, \
            "Annexe 3 doit encadrer les accès"
        assert "journalisation" in a3_lower or "log" in a3_lower or "traçabilité" in a3_lower, \
            "Annexe 3 doit mentionner la journalisation"

    def test_annexe_4_dpa_conditional(self):
        """Annexe 4 (DPA RGPD) doit être conditionnelle (accès distant seulement)."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a4 = get_template_pack()["ANNEXE_4"]
        a4_lower = a4.lower()
        assert "article 28" in a4_lower or "art. 28" in a4_lower or "rgpd" in a4_lower, \
            "Annexe 4 doit référencer l'art. 28 RGPD"

    def test_annexe_5_reversibility_no_code_transfer(self):
        """Annexe 5 (réversibilité) NE DOIT PAS promettre de remise de code."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a5 = get_template_pack()["ANNEXE_5"]
        a5_lower = a5.lower()
        forbidden = ["remise du code source", "livraison du code", "code source livré"]
        for phrase in forbidden:
            assert phrase not in a5_lower, \
                f"Annexe 5 contient une clause dangereuse: '{phrase}'"
        # Doit mentionner suppression des accès
        assert "suppression" in a5_lower or "désactivation" in a5_lower, \
            "Annexe 5 doit mentionner la suppression/désactivation des accès"

    def test_annexe_6_pricing_has_payment_terms(self):
        """Annexe 6 (grille tarifaire) doit contenir les conditions de paiement."""
        from python.helpers.contract_drafting.templates import get_template_pack
        a6 = get_template_pack()["ANNEXE_6"]
        a6_lower = a6.lower()
        assert "paiement" in a6_lower or "facturation" in a6_lower, \
            "Annexe 6 doit contenir les conditions de paiement"

    def test_all_templates_have_disclaimer(self):
        """Chaque section doit contenir ou être accompagnée d'un disclaimer."""
        from python.helpers.contract_drafting.templates import get_template_pack
        pack = get_template_pack()
        # Au minimum le CP doit rappeler que c'est un projet
        cp = pack["CP"]
        assert "projet" in cp.lower() or "valider" in cp.lower() or "PROJET" in cp, \
            "Le CP doit mentionner que c'est un PROJET à valider"

    def test_render_template_replaces_variables(self):
        """Le rendu doit remplacer les variables par leurs valeurs."""
        from python.helpers.contract_drafting.templates import render_template
        template = "Le Client {client_name} et l'Éditeur {editor_name}."
        result = render_template(template, {"client_name": "DICA France", "editor_name": "KOREV"})
        assert "DICA France" in result
        assert "KOREV" in result
        assert "{client_name}" not in result

    def test_render_template_leaves_missing_vars_marked(self):
        """Les variables non fournies doivent rester marquées visiblement."""
        from python.helpers.contract_drafting.templates import render_template
        template = "Prix: {monthly_fee} EUR/mois"
        result = render_template(template, {})
        # La variable manquante doit être visible (pas disparaître silencieusement)
        assert "monthly_fee" in result or "[À COMPLÉTER]" in result


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: LEAK GUARD (Act Leak Guard)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeakGuard:
    """Tests du Act Leak Guard — détection de clauses dangereuses."""

    def test_detects_code_source_transfer(self):
        """Doit détecter 'remise du code source' comme P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Article 12: Le prestataire procédera à la remise du code source au Client."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Remise du code source doit être P0"

    def test_detects_cession_ip(self):
        """Doit détecter 'cession' de propriété intellectuelle comme P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "La cession de tous les droits de propriété intellectuelle est incluse."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "'Cession' de PI doit être P0"

    def test_detects_knowhow_transfer(self):
        """Doit détecter le transfert de savoir-faire comme P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le prestataire transmet son savoir-faire technique au Client."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Transfert de savoir-faire doit être P0"

    def test_detects_zero_risk_guarantee(self):
        """Doit détecter 'garantie zéro risque' comme P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le prestataire garantit une solution zéro risque et sans faille."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "'Zéro risque' doit être P0"

    def test_detects_24_7_without_scope(self):
        """Doit détecter un SLA '24/7' non encadré comme P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le support est assuré 24h/24 et 7j/7."
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "SLA 24/7 non encadré doit être au minimum P1"

    def test_detects_conformite_totale(self):
        """Doit détecter 'conformité totale' comme P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le logiciel garantit une conformité totale au RGPD."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "'Conformité totale' doit être P0"

    def test_clean_contract_no_p0(self):
        """Un contrat propre ne doit avoir aucun P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = """
        Article 1: L'Éditeur accorde au Client une licence d'usage non exclusive,
        non cessible et non transférable du Logiciel, pour un usage strictement interne.
        
        Article 2: La propriété intellectuelle du Logiciel reste entièrement acquise 
        à l'Éditeur. Aucun transfert de droits n'est opéré par le présent contrat.
        
        Article 3: Le plafond de responsabilité est limité au montant payé sur les 
        12 derniers mois.
        """
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) == 0, f"Contrat propre ne doit avoir aucun P0, trouvé: {[f.pattern for f in p0s]}"

    def test_detects_code_source_variants(self):
        """Doit détecter les variantes de 'code source'."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        
        variants = [
            "Le code source sera livré au Client",
            "Accès au repository Git du code",
            "Les sources du logiciel seront remises",
        ]
        for text in variants:
            findings = scan_for_leaks(text)
            p0s = [f for f in findings if f.severity == FindingSeverity.P0]
            assert len(p0s) >= 1, f"Variante non détectée: '{text}'"

    def test_scan_returns_section_info(self):
        """Chaque finding doit identifier la section concernée."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks_by_section
        sections = {
            "CG": "La cession du code source est prévue à l'article 5.",
            "ANNEXE_5": "Restitution des dernières versions livrées.",
        }
        findings = scan_for_leaks_by_section(sections)
        assert any(f.section == "CG" for f in findings), \
            "Le finding doit identifier la section CG"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: GATE (Audit Gate — fail-closed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGate:
    """Tests de la gate d'audit (fail-closed)."""

    def test_gate_reject_on_p0(self):
        """La gate DOIT rejeter si un P0 est trouvé."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={
                "CP": "...",
                "CG": "Le prestataire procédera à la remise du code source.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="test-gate-p0",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT, \
            "Gate DOIT rejeter quand P0 trouvé"
        assert verdict.can_release is False
        assert verdict.has_p0() is True

    def test_gate_approve_clean_contract(self):
        """La gate DOIT approuver un contrat propre (pas de P0, toutes sections)."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={
                "CP": "Le Client DICA France obtient une licence d'usage.",
                "CG": "La propriété intellectuelle reste acquise à l'Éditeur. "
                       "Plafond de responsabilité: montant payé sur 12 mois.",
                "ANNEXE_1": "Description du logiciel DICA Decor.",
                "ANNEXE_2": "Support et maintenance — niveaux P1/P2/P3.",
                "ANNEXE_3": "Sécurité: accès distant encadré, journalisation.",
                "ANNEXE_4": "DPA RGPD — conditionnel si accès distant.",
                "ANNEXE_5": "Réversibilité et fin de contrat.",
                "ANNEXE_6": "Grille tarifaire et conditions de paiement.",
            },
            variables={"client_name": "DICA France"},
            disclaimer="PROJET — à valider par un juriste",
            correlation_id="test-gate-clean",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.APPROVE, \
            f"Gate devrait approuver un contrat propre, mais: {verdict.summary}"
        assert verdict.can_release is True

    def test_gate_reject_missing_disclaimer(self):
        """La gate DOIT rejeter si le disclaimer est absent."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={"CP": "...", "CG": "..."},
            variables={},
            disclaimer="",  # Empty disclaimer
            correlation_id="test-gate-no-disclaimer",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT, \
            "Gate DOIT rejeter sans disclaimer"

    def test_gate_p1_findings_warn_but_allow(self):
        """Les P1 doivent être signalés mais n'empêchent pas la release (sauf si P0)."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import (
            ContractDraft, GateVerdictEnum, FindingSeverity,
        )
        draft = ContractDraft(
            sections={
                "CP": "...",
                "CG": "Le support est assuré 24h/24 7j/7. "
                       "La propriété intellectuelle reste acquise à l'Éditeur.",
            },
            variables={},
            disclaimer="PROJET — à valider par un juriste",
            correlation_id="test-gate-p1",
        )
        verdict = run_gate(draft)
        # P1 only — should still allow release with warnings
        p1s = [f for f in verdict.findings if f.severity == FindingSeverity.P1]
        assert len(p1s) >= 1, "Doit détecter le 24/7 comme P1"
        # No P0 → can release
        if not verdict.has_p0():
            assert verdict.can_release is True

    def test_gate_fail_closed_invariant(self):
        """INVARIANT: can_release=True UNIQUEMENT si verdict=APPROVE."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        # Contrat avec P0
        draft = ContractDraft(
            sections={"CG": "Cession totale du code source et du savoir-faire."},
            variables={},
            disclaimer="PROJET",
            correlation_id="test-invariant",
        )
        verdict = run_gate(draft)
        if verdict.verdict == GateVerdictEnum.REJECT:
            assert verdict.can_release is False, \
                "INVARIANT VIOLÉ: REJECT avec can_release=True"
        if verdict.can_release is True:
            assert verdict.verdict == GateVerdictEnum.APPROVE, \
                "INVARIANT VIOLÉ: can_release=True sans APPROVE"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: ORCHESTRATOR (Draft → Gate → Output)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrator:
    """Tests du pipeline Draft → Gate → Output."""

    def test_generate_contract_returns_draft(self):
        """generate_contract doit retourner un ContractDraft."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        from python.helpers.contract_drafting.models import ContractDraft
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Tribunal de commerce de Grenoble",
        }
        draft = generate_contract(variables, contract_type="on_prem_licence")
        assert isinstance(draft, ContractDraft)
        assert "CP" in draft.sections
        assert "CG" in draft.sections
        assert draft.disclaimer != ""

    def test_generate_and_gate_clean_contract(self):
        """Un contrat généré proprement doit passer la gate."""
        from python.helpers.contract_drafting.orchestrator import (
            generate_contract, gate_contract,
        )
        from python.helpers.contract_drafting.models import GateVerdictEnum
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Tribunal de commerce de Grenoble",
        }
        draft = generate_contract(variables, contract_type="on_prem_licence")
        verdict = gate_contract(draft)
        assert verdict.verdict == GateVerdictEnum.APPROVE, \
            f"Contrat template propre devrait passer la gate: {verdict.summary}"

    def test_full_pipeline_returns_output(self):
        """Le pipeline complet doit retourner un DraftingOutput."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import DraftingOutput
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Tribunal de commerce de Grenoble",
        }
        output = run_drafting_pipeline(variables, contract_type="on_prem_licence")
        assert isinstance(output, DraftingOutput)
        assert output.gate_passed is True
        assert output.rendered_contract != ""

    def test_pipeline_fail_closed_on_tampered_draft(self):
        """Si le draft est modifié avec du P0, le pipeline doit fail-closed."""
        from python.helpers.contract_drafting.orchestrator import gate_contract
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        
        # Simulate a tampered draft with code source transfer
        tampered = ContractDraft(
            sections={
                "CP": "...",
                "CG": "L'Éditeur remet le code source complet au Client, "
                       "incluant la cession de tous droits patrimoniaux.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="test-tampered",
        )
        verdict = gate_contract(tampered)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: ROUTER (intent contract_drafting → legal_drafting_guarded)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContractDraftingRouter:
    """Tests du routage vers legal_drafting_guarded."""

    def test_detect_contract_drafting_intent(self):
        """Doit détecter l'intent contract_drafting."""
        from python.helpers.contract_drafting.orchestrator import detect_contract_drafting_intent
        queries = [
            "Rédige un contrat de licence entre KOREV et DICA France",
            "Produire un CONTRAT prêt à signature",
            "Draft a software license agreement",
            "Prépare les conditions générales pour une licence logiciel",
        ]
        for q in queries:
            assert detect_contract_drafting_intent(q) is True, \
                f"Intent non détecté pour: '{q[:60]}...'"

    def test_non_contract_queries_not_matched(self):
        """Les requêtes non contractuelles ne doivent pas matcher."""
        from python.helpers.contract_drafting.orchestrator import detect_contract_drafting_intent
        queries = [
            "Qu'est-ce qu'un contrat synallagmatique ?",
            "Analyse les risques de ce contrat",
            "Quelle est la météo à Paris ?",
        ]
        for q in queries:
            assert detect_contract_drafting_intent(q) is False, \
                f"Faux positif pour: '{q}'"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: INVARIANTS DE SÉCURITÉ
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityInvariants:
    """Tests des invariants de sécurité — zéro fuite, RGPD conditionnelle."""

    def test_on_prem_no_code_transfer_in_any_section(self):
        """INVARIANT: Aucune section du contrat on-prem ne doit contenir de remise code."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Tribunal de commerce de Grenoble",
        }
        draft = generate_contract(variables, contract_type="on_prem_licence")
        
        forbidden = [
            "remise du code source",
            "livraison du code source",
            "cession du code",
            "transfert du code source",
            "sources du logiciel remises",
        ]
        for section_name, section_text in draft.sections.items():
            text_lower = section_text.lower()
            for phrase in forbidden:
                assert phrase not in text_lower, \
                    f"FUITE DÉTECTÉE dans {section_name}: '{phrase}'"

    def test_dpa_conditional_on_remote_access(self):
        """INVARIANT: DPA RGPD (Annexe 4) activée UNIQUEMENT si accès distant."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        
        # Sans accès distant → DPA optionnelle (marquée comme conditionnelle)
        draft_no_remote = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "false"},
            contract_type="on_prem_licence",
        )
        a4 = draft_no_remote.sections.get("ANNEXE_4", "")
        # Should indicate it's conditional/optional
        assert "conditionnel" in a4.lower() or "optionnel" in a4.lower() or \
               "si applicable" in a4.lower() or "non applicable" in a4.lower() or \
               "uniquement" in a4.lower(), \
            "DPA doit être marquée comme conditionnelle quand pas d'accès distant"

    def test_dpa_mandatory_with_remote_support(self):
        """INVARIANT: Si accès support distant → DPA OBLIGATOIRE."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        draft_remote = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "true"},
            contract_type="on_prem_licence",
        )
        a4 = draft_remote.sections.get("ANNEXE_4", "")
        a4_lower = a4.lower()
        # Must contain substantive DPA content
        assert "sous-traitant" in a4_lower or "responsable de traitement" in a4_lower or \
               "article 28" in a4_lower or "données personnelles" in a4_lower, \
            "DPA doit être substantive quand accès distant activé"

    def test_cp_primacy_over_cg(self):
        """INVARIANT: Les CP doivent primer sur les CG (art. 1171)."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        variables = {
            "client_name": "DICA France", "editor_name": "KOREV",
            "software_name": "DICA Decor", "jurisdiction": "Grenoble",
        }
        draft = generate_contract(variables, contract_type="on_prem_licence")
        
        # Check CG mentions CP primacy
        all_text = " ".join(draft.sections.values()).lower()
        assert "conditions particulières" in all_text and \
               ("priment" in all_text or "prévalent" in all_text or "primauté" in all_text), \
            "Le contrat doit stipuler la primauté des CP sur les CG"

    def test_liability_capped(self):
        """INVARIANT: La responsabilité doit être plafonnée."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        variables = {
            "client_name": "DICA France", "editor_name": "KOREV",
            "software_name": "DICA Decor", "jurisdiction": "Grenoble",
        }
        draft = generate_contract(variables, contract_type="on_prem_licence")
        all_text = " ".join(draft.sections.values()).lower()
        assert "plafond" in all_text or "plafonné" in all_text or \
               "ne saurait excéder" in all_text or "limité" in all_text, \
            "La responsabilité doit être plafonnée"

    def test_no_absolute_guarantees(self):
        """INVARIANT: Aucune garantie absolue (zéro bug, zéro risque, etc.)."""
        from python.helpers.contract_drafting.orchestrator import generate_contract
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        variables = {
            "client_name": "DICA France", "editor_name": "KOREV",
            "software_name": "DICA Decor", "jurisdiction": "Grenoble",
        }
        draft = generate_contract(variables, contract_type="on_prem_licence")
        all_text = " ".join(draft.sections.values())
        findings = scan_for_leaks(all_text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) == 0, \
            f"Garanties absolues détectées: {[f.pattern for f in p0s]}"

    def test_legal_safe_still_refuses_drafting(self):
        """INVARIANT: legal_safe REFUSE toujours la rédaction directe."""
        # Verify the prompt still contains the refusal
        import os
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agents", "legal_safe", "prompts", "agent.system.main.role.md"
        )
        if os.path.exists(prompt_path):
            with open(prompt_path) as f:
                content = f.read()
            assert "actes interdits" in content.lower() or "rédaction d'actes juridiques" in content.lower(), \
                "legal_safe doit toujours refuser la rédaction d'actes juridiques"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: SCÉNARIOS E2E
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EScenarios:
    """Tests E2E — scénarios réels KOREV/DICA."""

    def test_scenario_on_prem_licence_complete(self):
        """Scénario complet: licence on-prem KOREV/DICA France."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        
        variables = {
            "client_name": "DICA France",
            "client_address": "123 rue de l'Industrie, 38000 Grenoble",
            "client_siret": "123 456 789 00012",
            "editor_name": "KOREV",
            "editor_address": "456 avenue de la Technologie, 38000 Grenoble",
            "software_name": "DICA Decor",
            "jurisdiction": "Tribunal de commerce de Grenoble",
            "licence_metric": "par poste",
            "initial_posts": "1",
            "max_posts": "4",
            "remote_access": "false",
        }
        output = run_drafting_pipeline(variables, contract_type="on_prem_licence")
        
        # Must pass gate
        assert output.gate_passed is True, f"Gate failed: {output.gate_summary}"
        
        # Must contain all sections
        assert "CP" in output.draft.sections
        assert "CG" in output.draft.sections
        assert "ANNEXE_1" in output.draft.sections
        assert "ANNEXE_2" in output.draft.sections
        
        # Client name must appear in rendered contract
        assert "DICA France" in output.rendered_contract
        assert "KOREV" in output.rendered_contract

    def test_scenario_remote_support_forces_dpa(self):
        """Scénario: accès support distant → DPA obligatoire."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        
        variables = {
            "client_name": "DICA France",
            "editor_name": "KOREV",
            "software_name": "DICA Decor",
            "jurisdiction": "Grenoble",
            "remote_access": "true",
        }
        output = run_drafting_pipeline(variables, contract_type="on_prem_licence")
        
        assert output.gate_passed is True
        a4 = output.draft.sections.get("ANNEXE_4", "")
        assert len(a4) > 100, "DPA doit être substantive avec accès distant"

    def test_scenario_sla_too_strong_rejected(self):
        """Scénario: SLA trop fort (24/7 promis) → gate KO si P0."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, FindingSeverity
        
        # Simulated draft with unrealistic SLA
        draft = ContractDraft(
            sections={
                "CP": "...",
                "CG": "Le prestataire garantit une conformité totale et un support 24/7.",
                "ANNEXE_2": "Disponibilité garantie 99.999% — zéro interruption.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="test-sla-too-strong",
        )
        verdict = run_gate(draft)
        assert verdict.has_p0() is True, \
            "SLA irréaliste doit déclencher P0"
        assert verdict.can_release is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

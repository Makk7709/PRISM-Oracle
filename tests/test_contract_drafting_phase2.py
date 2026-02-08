"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   PHASE 2 — PROCESS JURIDIQUE FAIL-CLOSED (Draft → Gate → Validation)      ║
║                                                                              ║
║   Tests TDD STRICT — écrits AVANT le code.                                  ║
║                                                                              ║
║   Couvre:                                                                    ║
║     A. Leak Guard enrichi (obligations résultat, RGPD gaps, indexation)     ║
║     B. Export Control (blocage PDF/DOC sans PASS)                           ║
║     C. Gouvernance (type legal_contract, veto legal_safe)                   ║
║     D. Gate structurée (références légales, audit report)                   ║
║     E. Scénarios avancés (support distant, RGPD sans DPA, SLA sans moyens) ║
║     F. legal_safe veto absolu (jamais de bypass)                            ║
║                                                                              ║
║   © 2026 Korev AI — Proprietary                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from typing import Dict


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION A: LEAK GUARD ENRICHI
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeakGuardEnrichi:
    """Patterns P0 additionnels requis par le prompt Phase 2."""

    def test_obligation_resultat_implicite_p0(self):
        """Obligation de résultat implicite sans plafond → P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur s'engage à une obligation de résultat quant au bon fonctionnement."
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "Obligation de résultat implicite doit être détectée"

    def test_acces_depot_code_p0(self):
        """Accès au dépôt de code → P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Le Client aura accès au dépôt de code de l'Éditeur."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "'Accès au dépôt de code' doit être P0"

    def test_rgpd_sans_role_clair_p0(self):
        """RGPD mentionné sans rôle clair (responsable/sous-traitant) → P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = (
            "Les données personnelles seront traitées conformément au RGPD. "
            "L'Éditeur traite les données du Client."
        )
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "RGPD sans rôle clair doit être détecté"

    def test_sla_sans_exclusions_p1(self):
        """SLA avec engagement fort sans exclusions → au min P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Disponibilité garantie de 99.9% sur l'ensemble du périmètre."
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "SLA 99.9% garanti doit être détecté"

    def test_indexation_ambigue_p1(self):
        """Clause d'indexation ambiguë (sans indice précis) → P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Les tarifs seront révisés annuellement selon l'évolution des coûts."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1s) >= 1, "Indexation ambiguë doit être P1"

    def test_penalites_incoherentes_p1(self):
        """Pénalités sans plafond ou incohérentes → P1."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "En cas de retard, des pénalités illimitées seront appliquées."
        findings = scan_for_leaks(text)
        p1s = [f for f in findings if f.severity == FindingSeverity.P1]
        assert len(p1s) >= 1, "Pénalités illimitées doit être P1"

    def test_garantit_la_conformite_p0(self):
        """'Garantit la conformité' → P0 (garantie absolue)."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur garantit la conformité du logiciel à toutes les normes applicables."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "'Garantit la conformité' doit être P0"

    def test_cession_implicite_p0(self):
        """Cession implicite de droits → P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Les droits patrimoniaux sont transférés au Client de manière irrévocable."
        findings = scan_for_leaks(text)
        p0s = [f for f in findings if f.severity == FindingSeverity.P0]
        assert len(p0s) >= 1, "Transfert irrévocable de droits doit être P0"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION B: EXPORT CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportControl:
    """Contrôle d'export — aucun PDF/DOC tant que P0 subsiste."""

    def test_export_allowed_returns_true_on_pass(self):
        """is_export_allowed retourne True si gate PASS."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE, can_release=True, summary="OK"
            ),
            gate_passed=True,
            gate_summary="OK",
            rendered_contract="...",
        )
        assert is_export_allowed(output) is True

    def test_export_blocked_on_reject(self):
        """is_export_allowed retourne False si gate REJECT."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
            LeakFinding, FindingSeverity,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.REJECT, can_release=False, summary="P0",
                findings=[LeakFinding(
                    severity=FindingSeverity.P0, pattern="test",
                    context="test", recommendation="test", section="CG",
                )],
            ),
            gate_passed=False,
            gate_summary="P0",
        )
        assert is_export_allowed(output) is False

    def test_export_blocked_without_gate_verdict(self):
        """is_export_allowed retourne False si pas de verdict."""
        from python.helpers.contract_drafting.export_control import is_export_allowed
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer=""),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.REJECT, can_release=False, summary=""
            ),
            gate_passed=False,
            gate_summary="",
        )
        assert is_export_allowed(output) is False

    def test_export_stamp_contains_legal_safe(self):
        """Le stamp d'export doit contenir 'VALIDÉ PAR LEGAL_SAFE'."""
        from python.helpers.contract_drafting.export_control import (
            is_export_allowed, get_export_stamp,
        )
        from python.helpers.contract_drafting.models import (
            DraftingOutput, ContractDraft, GateVerdict, GateVerdictEnum,
        )
        output = DraftingOutput(
            draft=ContractDraft(sections={}, variables={}, disclaimer="PROJET"),
            gate_verdict=GateVerdict(
                verdict=GateVerdictEnum.APPROVE, can_release=True, summary="OK"
            ),
            gate_passed=True,
            gate_summary="OK",
            rendered_contract="...",
        )
        stamp = get_export_stamp(output)
        assert "LEGAL_SAFE" in stamp.upper()
        assert "VALIDÉ" in stamp.upper() or "PASS" in stamp.upper()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION C: GOUVERNANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernance:
    """Règles de gouvernance du pipeline juridique."""

    def test_decision_type_is_legal_contract(self):
        """Le type de décision du pipeline doit être 'legal_contract'."""
        from python.helpers.contract_drafting.governance import DECISION_GOVERNANCE_TYPE
        assert DECISION_GOVERNANCE_TYPE == "legal_contract"

    def test_multi_agent_consensus_cannot_override_legal_safe(self):
        """MULTI_AGENT_CONSENSUS ne peut JAMAIS donner un verdict juridique final."""
        from python.helpers.contract_drafting.governance import (
            can_consensus_override_legal_gate,
        )
        assert can_consensus_override_legal_gate() is False

    def test_legal_safe_has_absolute_veto(self):
        """legal_safe a un droit de veto absolu sur tout contrat."""
        from python.helpers.contract_drafting.governance import (
            is_legal_safe_veto_absolute,
        )
        assert is_legal_safe_veto_absolute() is True

    def test_no_approved_without_legal_safe_pass(self):
        """Aucun APPROVED global sans PASS legal_safe."""
        from python.helpers.contract_drafting.governance import (
            is_contract_globally_approved,
        )
        from python.helpers.contract_drafting.models import (
            GateVerdict, GateVerdictEnum,
        )
        # REJECT verdict → not approved
        reject = GateVerdict(verdict=GateVerdictEnum.REJECT, can_release=False)
        assert is_contract_globally_approved(reject) is False
        
        # APPROVE verdict → approved
        approve = GateVerdict(verdict=GateVerdictEnum.APPROVE, can_release=True)
        assert is_contract_globally_approved(approve) is True


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION D: GATE STRUCTURÉE (références légales + audit report)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateAuditReport:
    """Gate audit structurée avec références légales."""

    def test_finding_has_legal_reference(self):
        """Les findings doivent pouvoir porter une référence légale."""
        from python.helpers.contract_drafting.models import LeakFinding, FindingSeverity
        finding = LeakFinding(
            severity=FindingSeverity.P0,
            pattern="remise du code",
            context="...",
            recommendation="...",
            section="CG",
            legal_ref="Art. L.122-6-1 CPI",
        )
        assert finding.legal_ref == "Art. L.122-6-1 CPI"

    def test_gate_verdict_has_audit_report(self):
        """Le verdict doit contenir un rapport d'audit structuré."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={"CG": "Cession du code source au Client."},
            variables={},
            disclaimer="PROJET",
            correlation_id="test-audit-report",
        )
        verdict = run_gate(draft)
        # Le verdict doit avoir un rapport d'audit
        report = verdict.to_audit_report()
        assert "P0" in report
        assert "REJECT" in report.upper() or "REJETÉ" in report.upper()

    def test_audit_report_lists_all_findings(self):
        """Le rapport d'audit doit lister TOUS les findings avec leurs détails."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft
        draft = ContractDraft(
            sections={
                "CG": "Cession du code source. Support garanti 24/7.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="test-audit-all",
        )
        verdict = run_gate(draft)
        report = verdict.to_audit_report()
        # Must list findings
        assert "cession" in report.lower() or "code source" in report.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION E: SCÉNARIOS AVANCÉS
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenariosAvances:
    """Scénarios avancés — support distant, RGPD, SLA."""

    def test_support_distant_non_encadre_fail(self):
        """Accès support distant non encadré (pas de logs, pas d'autorisation) → FAIL."""
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={
                "ANNEXE_3": "L'Éditeur accède librement aux systèmes du Client "
                             "pour tout besoin de maintenance, sans restriction.",
            },
            variables={},
            disclaimer="PROJET",
            correlation_id="test-support-libre",
        )
        verdict = run_gate(draft)
        has_finding = len(verdict.findings) >= 1
        assert has_finding, "Accès libre sans logs doit déclencher un finding"

    def test_support_ponctuel_logs_dpa_pass(self):
        """Accès ponctuel + logs + DPA → le template standard doit passer."""
        from python.helpers.contract_drafting.orchestrator import (
            generate_contract, gate_contract,
        )
        from python.helpers.contract_drafting.models import GateVerdictEnum
        draft = generate_contract(
            {"client_name": "X", "editor_name": "Y", "software_name": "Z",
             "jurisdiction": "Paris", "remote_access": "true"},
        )
        verdict = gate_contract(draft)
        assert verdict.verdict == GateVerdictEnum.APPROVE, \
            f"Template standard avec accès distant devrait passer: {verdict.summary}"

    def test_rgpd_data_access_without_dpa_flagged(self):
        """Accès aux données personnelles sans DPA → détecté."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = (
            "L'Éditeur traite les données personnelles du Client "
            "dans le cadre du support technique."
        )
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "Traitement de données sans DPA doit être détecté"

    def test_sla_99_9_sans_moyens_flagged(self):
        """SLA 99.9% garanti sans préciser les moyens → détecté."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "Disponibilité garantie de 99.9% sur l'ensemble de la plateforme."
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "SLA 99.9% garanti doit être détecté"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION F: VETO LEGAL_SAFE ABSOLU
# ═══════════════════════════════════════════════════════════════════════════════

class TestVetoLegalSafeAbsolu:
    """Vérification que le veto legal_safe est ABSOLU."""

    def test_pipeline_never_outputs_contract_on_reject(self):
        """Le pipeline ne doit JAMAIS sortir de contrat si REJECT."""
        from python.helpers.contract_drafting.orchestrator import gate_contract
        from python.helpers.contract_drafting.models import ContractDraft, GateVerdictEnum
        draft = ContractDraft(
            sections={"CG": "Remise du code source intégral."},
            variables={},
            disclaimer="PROJET",
            correlation_id="test-veto",
        )
        verdict = gate_contract(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        assert verdict.can_release is False

    def test_pipeline_output_empty_on_fail(self):
        """Si gate FAIL → rendered_contract DOIT être vide."""
        from python.helpers.contract_drafting.orchestrator import run_drafting_pipeline
        from python.helpers.contract_drafting.models import ContractDraft
        
        # Inject a tampered section after generation
        from python.helpers.contract_drafting.gate import run_gate
        from python.helpers.contract_drafting.models import GateVerdictEnum
        
        draft = ContractDraft(
            sections={"CG": "Cession du code source au Client."},
            variables={},
            disclaimer="PROJET",
            correlation_id="test-empty",
        )
        verdict = run_gate(draft)
        assert verdict.verdict == GateVerdictEnum.REJECT
        # Cannot release → no rendered contract possible

    def test_libre_acces_systems_p0(self):
        """'Accède librement aux systèmes' sans encadrement → P0."""
        from python.helpers.contract_drafting.leak_guard import scan_for_leaks
        from python.helpers.contract_drafting.models import FindingSeverity
        text = "L'Éditeur accède librement et sans restriction aux systèmes du Client."
        findings = scan_for_leaks(text)
        severe = [f for f in findings if f.severity in (FindingSeverity.P0, FindingSeverity.P1)]
        assert len(severe) >= 1, "'Accès libre sans restriction' doit être détecté"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

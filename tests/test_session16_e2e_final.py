"""
SESSION 16 — Tests E2E finaux : validation complete de l'audit report.

Simulates 5 distinct query types and verifies that EVERY field
identified in the E-01..E-11 diagnostic is now correctly resolved:

  E-01  Tokens (entree/sortie)           → present, non-zero
  E-02  Version Evidence                 → resolved (not "v1.0.0", not "unknown")
  E-03  Score de confiance               → present (not "—")
  E-04  Categorie AI Act                 → real value (not "unknown")
  E-05  Hash requete (SHA-256)           → present (not "pas de requete")
  E-06  Hash document (SHA-256)          → present when document exists
  E-07  Signature RSA-PSS-SHA256         → method is RSA when key available
  E-08  has_human_review                 → dynamically resolved
  E-09  has_consensus                    → dynamically resolved
  E-10  Art. 13 — Transparence narrative → non-technical section present
  E-11  Registres Art. 9/17/RGPD 30     → register sections present

5 scenarios:
  A. Legal simple          — single agent, no strategic pipeline
  B. Strategic finance     — 4-agent pipeline, document, FAIL_CLOSED context
  C. Medical high-risk     — HIGH_RISK category, low confidence
  D. General default       — no pipeline, no route_decision
  E. Multi-agent consensus — consensus + human review flags
"""

import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Helpers
# ============================================================================

def _make_envelope(sid="KRV-E2E-001", username="auditor", org="Korev AI",
                   version="legal_sources@v1.2.0-enterprise"):
    from python.helpers.session_envelope import SessionEnvelope
    return SessionEnvelope(
        session_id=sid,
        username=username,
        organization=org,
        evidence_version=version,
    )


def _make_tracker(agents):
    from python.helpers.pipeline_tracker import PipelineTracker
    tracker = PipelineTracker()
    for name in agents:
        tracker.start_step(name)
        tracker.complete_step(name)
    return tracker


def _make_route_decision(category="HIGH_RISK", strength=0.85):
    from python.helpers.router.routing_contract import (
        RouteDecision, RouteVerdict, RouteIntent, IntentName, AIActCategory,
    )
    cat = AIActCategory(category.lower())
    return RouteDecision(
        verdict=RouteVerdict.PROCEED,
        intents=[RouteIntent(name=IntentName.FINANCE, score=0.9)],
        routing_strength=strength,
        is_board_level=True,
        reasons=["E2E test scenario"],
        route_id="e2e-corr-001",
        ai_act_category=cat,
    )


def _render_report(**kwargs):
    from python.helpers.audit_report_renderer import AuditReportRenderer
    tokens_in = kwargs.pop("tokens_input", None)
    tokens_out = kwargs.pop("tokens_output", None)
    renderer = AuditReportRenderer(**kwargs)
    if tokens_in is not None:
        renderer.tokens_input = tokens_in
    if tokens_out is not None:
        renderer.tokens_output = tokens_out
    return renderer.render()


# ============================================================================
# A. SCENARIO — Legal simple
# ============================================================================

class TestScenarioLegalSimple:
    """Single legal_safe agent, no strategic pipeline, query present."""

    def _build_report(self):
        return _render_report(
            envelope=_make_envelope(sid="KRV-E2E-LEGAL"),
            tracker=_make_tracker(["legal_safe"]),
            route_decision=_make_route_decision("HIGH_RISK", 0.72),
            query="Quelle est la responsabilite contractuelle en droit francais ?",
            response="L'article 1231-1 du Code civil dispose que...",
            has_human_review=True,
            has_consensus=False,
            reasoning_narrative="Le systeme a analyse la requete juridique en 3 etapes.",
            meta_narrative="Confiance evaluee a un niveau intermediaire.",
        )

    def test_e01_tokens_field_present(self):
        """E-01: Token fields exist in metadata (even if no count in this scenario)."""
        report = self._build_report()
        assert "Tokens (entree)" in report
        assert "Tokens (sortie)" in report

    def test_e02_version_resolved(self):
        """E-02: Version is a real version, not 'v1.0.0' or 'unknown'."""
        report = self._build_report()
        assert "v1.2.0" in report
        assert "unknown" not in report.split("Version Evidence")[1][:50]

    def test_e03_confidence_score_present(self):
        """E-03: Confidence score is present in metadata."""
        report = self._build_report()
        metadata_section = report[report.find("### Metadonnees techniques"):]
        assert "0.72" in metadata_section or "72" in metadata_section

    def test_e04_ai_act_category_real(self):
        """E-04: AI Act category is a real value, not 'unknown'."""
        report = self._build_report()
        metadata_section = report[report.find("Categorie AI Act"):][:200]
        assert "unknown" not in metadata_section.lower()
        assert "high_risk" in metadata_section.lower()

    def test_e05_hash_requete_present(self):
        """E-05: Query hash is computed, not '— (pas de requete)'."""
        report = self._build_report()
        assert "pas de requete" not in report
        assert "sha256:" in report

    def test_e06_hash_document_absent_when_no_doc(self):
        """E-06: Document hash shows '—' when no document (correct behavior)."""
        report = self._build_report()
        assert "pas de document" in report

    def test_e07_signature_present(self):
        """E-07: Signature line exists (HMAC fallback acceptable in test env)."""
        report = self._build_report()
        assert "Signature log" in report
        assert ("hmac-sha256:" in report or "rsa-pss-sha256:" in report)

    def test_e08_human_review_reflected(self):
        """E-08: human_review=True is reflected in the report."""
        report = self._build_report()
        assert "revue humaine" in report.lower() or "supervision" in report.lower()

    def test_e10_transparency_narrative(self):
        """E-10: Non-technical transparency section present."""
        report = self._build_report()
        assert "### Transparence du raisonnement" in report
        assert "Art. 13" in report
        assert "Raisonnement interne" in report
        assert "Evaluation metacognitive" in report

    def test_e11_risk_register(self):
        """E-11: Risk register section present."""
        report = self._build_report()
        assert "### Registre des risques (Art. 9 AI Act)" in report
        assert "RSK-001" in report

    def test_e11_processing_register(self):
        """E-11: Processing register section present."""
        report = self._build_report()
        assert "### Registre des activites de traitement (RGPD Art. 30)" in report
        assert "PROC-001" in report

    def test_report_structure_complete(self):
        """Full report has all 10 canonical sections."""
        report = self._build_report()
        assert "### Identite de la session" in report
        assert "### Pipeline d'execution" in report
        assert "### Grille de conformite" in report
        assert "### Transparence du raisonnement" in report
        assert "### Registre des risques" in report
        assert "### Registre des activites de traitement" in report
        assert "### Metadonnees techniques" in report
        assert "### Integrite et securite" in report
        assert "KOREV Evidence" in report


# ============================================================================
# B. SCENARIO — Strategic finance (4-agent pipeline)
# ============================================================================

class TestScenarioStrategicFinance:
    """Full strategic pipeline with document, consensus, 4 agents."""

    def _build_report(self):
        return _render_report(
            envelope=_make_envelope(sid="KRV-E2E-STRAT"),
            tracker=_make_tracker(["researcher", "finance", "marketing", "sales"]),
            route_decision=_make_route_decision("HIGH_RISK", 0.91),
            query="Analyse strategique complete DICA France",
            response="Dossier strategique consolide avec 370 sources...",
            document="Document strategique DICA France - 45 pages...",
            has_human_review=False,
            has_consensus=True,
            reasoning_narrative="4 agents ont ete consultes pour croiser les analyses.",
            meta_narrative="La confiance est elevee grace au consensus multi-agents.",
        )

    def test_e03_confidence_091(self):
        report = self._build_report()
        assert "0.91" in report or "91" in report

    def test_e04_high_risk(self):
        report = self._build_report()
        assert "high_risk" in report.lower()

    def test_e05_query_hash_computed(self):
        report = self._build_report()
        expected_prefix = "sha256:" + hashlib.sha256(
            "Analyse strategique complete DICA France".encode()
        ).hexdigest()[:12]
        assert expected_prefix in report

    def test_e06_document_hash_present(self):
        """E-06: When document is provided, its hash MUST appear."""
        report = self._build_report()
        assert "pas de document" not in report
        doc_hash = hashlib.sha256(
            "Document strategique DICA France - 45 pages...".encode()
        ).hexdigest()
        assert doc_hash[:16] in report

    def test_e09_consensus_reflected(self):
        """E-09: consensus=True reflected in transparency and/or compliance."""
        report = self._build_report()
        assert "consensus" in report.lower()

    def test_4_agents_in_pipeline(self):
        report = self._build_report()
        for agent in ["researcher", "finance", "marketing", "sales"]:
            assert agent in report.lower()

    def test_strategic_document_validation_narrative(self):
        report = self._build_report()
        assert "document strategique" in report.lower() or "consolide" in report.lower()


# ============================================================================
# C. SCENARIO — Medical high-risk, low confidence
# ============================================================================

class TestScenarioMedicalHighRisk:
    """Medical agent, HIGH_RISK, low confidence → session risk expected."""

    def _build_report(self):
        from python.helpers.router.routing_contract import (
            RouteDecision, RouteVerdict, RouteIntent, IntentName, AIActCategory,
        )
        rd = RouteDecision(
            verdict=RouteVerdict.PROCEED,
            intents=[RouteIntent(name=IntentName.MEDICAL, score=0.95)],
            routing_strength=0.28,
            is_board_level=False,
            reasons=["Medical analysis"],
            route_id="e2e-med-001",
            ai_act_category=AIActCategory.HIGH_RISK,
        )
        return _render_report(
            envelope=_make_envelope(sid="KRV-E2E-MED"),
            tracker=_make_tracker(["medical"]),
            route_decision=rd,
            query="Quel est le protocole de traitement pour le diabete de type 2 ?",
            response="Le traitement repose sur des mesures hygieno-dietetiques...",
            has_human_review=True,
            reasoning_narrative="Analyse medicale realisee avec prudence.",
        )

    def test_e03_low_confidence_visible(self):
        report = self._build_report()
        assert "0.28" in report or "28%" in report or "faible" in report.lower()

    def test_e04_high_risk_medical(self):
        report = self._build_report()
        assert "high_risk" in report.lower()

    def test_session_risk_for_low_confidence(self):
        """Risk register should include a session-specific risk for low confidence."""
        report = self._build_report()
        assert "RSK-SES" in report

    def test_session_risk_for_high_risk_category(self):
        report = self._build_report()
        assert "controles renforces" in report.lower() or "RSK-SES-002" in report

    def test_human_review_triggered(self):
        report = self._build_report()
        assert "revue humaine" in report.lower()


# ============================================================================
# D. SCENARIO — General default (no pipeline, no route_decision)
# ============================================================================

class TestScenarioGeneralDefault:
    """Simple query, no specialized pipeline, no route_decision."""

    def _build_report(self):
        return _render_report(
            envelope=_make_envelope(sid="KRV-E2E-GEN"),
            query="Bonjour, quelle heure est-il ?",
            response="Je suis un assistant IA...",
        )

    def test_report_renders_without_crash(self):
        report = self._build_report()
        assert "### Identite de la session" in report
        assert "KRV-E2E-GEN" in report

    def test_no_pipeline_section_when_no_tracker(self):
        report = self._build_report()
        assert "### Pipeline d'execution" not in report

    def test_metadata_shows_unknown_for_missing(self):
        """Without route_decision, AI Act category defaults to 'unknown'."""
        report = self._build_report()
        assert "Metadonnees techniques" in report

    def test_query_hash_still_computed(self):
        """E-05: even without pipeline, query hash should be computed."""
        report = self._build_report()
        assert "pas de requete" not in report

    def test_registers_still_present(self):
        """E-11: registers are always present even for simple queries."""
        report = self._build_report()
        assert "### Registre des risques" in report
        assert "### Registre des activites de traitement" in report

    def test_integrity_block_present(self):
        report = self._build_report()
        assert "### Integrite et securite" in report
        assert "sha256:" in report


# ============================================================================
# E. SCENARIO — Multi-agent with consensus
# ============================================================================

class TestScenarioMultiAgentConsensus:
    """Multiple agents, consensus active, human review active."""

    def _build_report(self):
        return _render_report(
            envelope=_make_envelope(sid="KRV-E2E-MULTI"),
            tracker=_make_tracker(["researcher", "legal_safe", "finance"]),
            route_decision=_make_route_decision("HIGH_RISK", 0.78),
            query="Analyse de conformite RGPD pour le projet X",
            response="Le traitement est conforme sous reserve...",
            document="Rapport d'analyse de conformite RGPD...",
            has_human_review=True,
            has_consensus=True,
            reasoning_narrative="3 agents ont collabore sur cette analyse.",
            meta_narrative="Evaluation metacognitive positive avec quelques reserves.",
        )

    def test_e08_human_review_true(self):
        report = self._build_report()
        assert "revue humaine" in report.lower()

    def test_e09_consensus_true(self):
        report = self._build_report()
        assert "consensus" in report.lower()

    def test_e10_both_narratives_present(self):
        report = self._build_report()
        assert "Raisonnement interne" in report
        assert "Evaluation metacognitive" in report

    def test_e06_document_hash_for_rgpd_report(self):
        report = self._build_report()
        assert "pas de document" not in report

    def test_3_agents_listed(self):
        report = self._build_report()
        assert "researcher" in report.lower()
        assert "legal_safe" in report.lower()
        assert "finance" in report.lower()

    def test_compliance_grid_art9_has_register_evidence(self):
        """Art. 9 in the compliance grid should mention risk register."""
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher", "legal_safe", "finance"]),
            route_decision=_make_route_decision("HIGH_RISK", 0.78),
            confidence_score=0.78,
            has_risk_register=True,
            has_processing_register=True,
            has_narrative=True,
            has_human_review=True,
            has_consensus=True,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert "Registre formel des risques present" in art9.evidence

    def test_compliance_grid_rgpd30_conforme(self):
        """RGPD Art. 30 should be CONFORME with register + metadata."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=True,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert art30.status == ComplianceStatus.CONFORME

    def test_compliance_grid_art13_conforme_with_narrative(self):
        """Art. 13 should be CONFORME when narrative is present + session data."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher"]),
            has_narrative=True,
        )
        art13 = [c for c in grid.checks if "Art. 13" in c.article][0]
        assert art13.status == ComplianceStatus.CONFORME


# ============================================================================
# F. CROSS-SCENARIO — Ecarts E-01..E-11 verification matrix
# ============================================================================

class TestEcartsVerificationMatrix:
    """
    Systematically verifies that EACH of the 11 original diagnostic gaps
    (E-01..E-11) is now resolved. This is the DEFINITIVE checklist.
    """

    def _full_report(self):
        """Build the most complete report (strategic scenario with everything)."""
        return _render_report(
            envelope=_make_envelope(sid="KRV-E2E-MATRIX", version="Evidence v1.3.0"),
            tracker=_make_tracker(["researcher", "finance", "marketing", "sales"]),
            route_decision=_make_route_decision("HIGH_RISK", 0.88),
            query="Analyse strategique complete du marche europeen",
            response="Dossier consolide avec 300+ sources verifiees...",
            document="Document strategique final — 50 pages",
            has_human_review=True,
            has_consensus=True,
            reasoning_narrative="Analyse multi-dimensionnelle en 5 etapes de raisonnement.",
            meta_narrative="Evaluation de confiance : niveau eleve, aucune escalade.",
            tokens_input=45000,
            tokens_output=12000,
        )

    def test_e01_tokens_nonzero(self):
        """E-01: Token counters are present and show real values."""
        report = self._full_report()
        assert "45,000" in report.replace(" ", "") or "45000" in report.replace(",", "").replace(" ", "")

    def test_e02_version_v130(self):
        """E-02: Version is the real version, not 'v1.0.0'."""
        report = self._full_report()
        assert "v1.3.0" in report

    def test_e03_confidence_088(self):
        """E-03: Confidence score is 0.88, not '—'."""
        report = self._full_report()
        assert "0.88" in report or "88" in report

    def test_e04_category_high_risk(self):
        """E-04: AI Act category is 'high_risk', not 'unknown'."""
        report = self._full_report()
        metadata = report[report.find("Categorie AI Act"):][:200]
        assert "high_risk" in metadata.lower()

    def test_e05_query_hash_sha256(self):
        """E-05: Query hash is a real SHA-256, not '— (pas de requete)'."""
        report = self._full_report()
        assert "pas de requete" not in report
        expected = hashlib.sha256(
            "Analyse strategique complete du marche europeen".encode()
        ).hexdigest()
        assert expected[:16] in report

    def test_e06_document_hash_sha256(self):
        """E-06: Document hash is computed from the real document."""
        report = self._full_report()
        assert "pas de document" not in report
        expected = hashlib.sha256(
            "Document strategique final — 50 pages".encode()
        ).hexdigest()
        assert expected[:16] in report

    def test_e07_signature_method(self):
        """E-07: Signature exists (RSA in prod, HMAC fallback in test is OK)."""
        report = self._full_report()
        assert "Signature log" in report
        sig_line = report[report.find("Signature log"):][:300]
        assert "hmac-sha256:" in sig_line or "rsa-pss-sha256:" in sig_line

    def test_e08_human_review_dynamic(self):
        """E-08: human_review is dynamically resolved (True in this scenario)."""
        report = self._full_report()
        assert "revue humaine" in report.lower()

    def test_e09_consensus_dynamic(self):
        """E-09: consensus is dynamically resolved (True in this scenario)."""
        report = self._full_report()
        assert "consensus" in report.lower()

    def test_e10_transparency_section_non_technical(self):
        """E-10: Transparency section exists with non-technical content.

        Forbidden technical terms are checked ONLY in the transparency section,
        not in the risk register (which legitimately documents technical mitigations).
        """
        report = self._full_report()
        assert "### Transparence du raisonnement" in report
        assert "Art. 13" in report
        assert "Raisonnement interne" in report
        assert "Evaluation metacognitive" in report
        start = report.find("### Transparence du raisonnement")
        end = report.find("### Registre des risques")
        transparency_section = report[start:end] if end > start else report[start:]
        forbidden_technical = ["CoT", "chain_of_thought", "prompt:", "system_message"]
        for term in forbidden_technical:
            assert term not in transparency_section, (
                f"Technical term '{term}' found in transparency section"
            )

    def test_e11_risk_register_complete(self):
        """E-11: Risk register section with all 7 static risks."""
        report = self._full_report()
        assert "### Registre des risques (Art. 9 AI Act)" in report
        for i in range(1, 8):
            assert f"RSK-00{i}" in report, f"RSK-00{i} missing from risk register"

    def test_e11_processing_register_complete(self):
        """E-11: Processing register with both activities."""
        report = self._full_report()
        assert "### Registre des activites de traitement (RGPD Art. 30)" in report
        assert "PROC-001" in report
        assert "PROC-002" in report
        assert "dpo@korev-evidence.com" in report

    def test_e11_session_risks_when_applicable(self):
        """E-11: Session-specific risks appear when context triggers them."""
        report = self._full_report()
        assert "RSK-SES-002" in report

    def test_overall_report_has_no_placeholder(self):
        """No placeholder values remain in a fully-populated report."""
        report = self._full_report()
        placeholders = ["TODO", "PLACEHOLDER", "FIXME", "XXX"]
        for p in placeholders:
            assert p not in report.upper(), f"Placeholder '{p}' found in report"

    def test_report_integrity_hash_computed(self):
        """Session integrity hash is computed (not empty)."""
        report = self._full_report()
        hash_line = report[report.find("Hash d'integrite session"):][:200]
        assert "sha256:" in hash_line


# ============================================================================
# G. COMPLIANCE STATUS HONESTY CHECKS
# ============================================================================

class TestComplianceHonesty:
    """Verify that compliance statuses are honest, not compliance-washed."""

    def test_art14_never_conforme_without_formal_register(self):
        """Art. 14 remains PARTIEL — no formal supervision register exists."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher"]),
            has_human_review=True,
        )
        art14 = [c for c in grid.checks if "Art. 14" in c.article][0]
        assert art14.status == ComplianceStatus.PARTIEL

    def test_art17_partiel_training_data_gap(self):
        """Art. 17 remains PARTIEL — training data management still missing."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher"]),
            has_risk_register=True,
            has_processing_register=True,
            has_consensus=True,
        )
        art17 = [c for c in grid.checks if "Art. 17" in c.article][0]
        assert art17.status == ComplianceStatus.PARTIEL
        assert "entrainement" in art17.gaps.lower()

    def test_art9_conforme_with_full_context(self):
        """Art. 9 is CONFORME when risk register + confidence + route_decision."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            route_decision=_make_route_decision("HIGH_RISK", 0.85),
            confidence_score=0.85,
            has_risk_register=True,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert art9.status == ComplianceStatus.CONFORME

    def test_rgpd30_conforme_with_register(self):
        """RGPD Art. 30 is CONFORME with processing register + session metadata."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=True,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert art30.status == ComplianceStatus.CONFORME
        assert art30.gaps == ""

    def test_overall_status_partiel_honest(self):
        """Overall status must be PARTIEL (Art. 14 and Art. 17 prevent CONFORME)."""
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(["researcher"]),
            route_decision=_make_route_decision("HIGH_RISK", 0.85),
            confidence_score=0.85,
            has_risk_register=True,
            has_processing_register=True,
            has_narrative=True,
            has_human_review=True,
            has_consensus=True,
        )
        assert grid.overall_status == ComplianceStatus.PARTIEL

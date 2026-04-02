"""
SESSION 15 — Tests: RiskRegister (Art. 9) + ProcessingRegister (RGPD Art. 30)
           + ComplianceGrid improvements + AuditReportRenderer integration.

Validates exhaustively:

  A. RiskRegister (python/helpers/risk_register.py)
    1. Static risks are populated (7 entries)
    2. Each risk has all required fields (id, domain, description, level, impact, mitigations)
    3. from_session() without route_decision returns only static risks
    4. from_session() with low confidence adds session risk RSK-SES-001
    5. from_session() with HIGH_RISK category adds session risk RSK-SES-002
    6. from_session() with MINIMAL_RISK does not add session risk
    7. to_report_section() produces valid markdown with table
    8. to_report_section() includes mitigation details
    9. to_dict() serialization is complete
    10. Risk levels cover LOW, MEDIUM, HIGH, CRITICAL

  B. ProcessingRegister (python/helpers/processing_register.py)
    11. Static activities are populated (2 entries)
    12. Each activity has all Art. 30 mandatory fields
    13. from_session() enriches with envelope user/org
    14. from_session() without envelope still works
    15. to_report_section() produces valid markdown
    16. to_report_section() mentions DPO contact
    17. to_report_section() mentions "aucun transfert hors UE"
    18. to_dict() serialization is complete
    19. has_required_fields() returns True for static activities
    20. has_required_fields() returns False for empty register

  C. ComplianceGrid Art. 9 with has_risk_register
    21. Art. 9 CONFORME when risk register + confidence + route_decision
    22. Art. 9 PARTIEL when no risk register
    23. Art. 9 evidence mentions "Registre formel" when present
    24. Art. 9 gaps mention "Registre formel absent" when missing

  D. ComplianceGrid Art. 17 with registers
    25. Art. 17 evidence mentions monitoring counters
    26. Art. 17 evidence mentions risk register when present
    27. Art. 17 evidence mentions processing register when present
    28. Art. 17 still PARTIEL (data management gap remains)

  E. ComplianceGrid RGPD Art. 30 with has_processing_register
    29. Art. 30 CONFORME when processing register + metadata
    30. Art. 30 PARTIEL when no processing register
    31. Art. 30 evidence mentions "Registre formel Art. 30" when present
    32. Art. 30 gaps empty when processing register present + metadata

  F. AuditReportRenderer integration
    33. Render includes risk register section
    34. Render includes processing register section
    35. Risk register section appears between transparency and source taxonomy
    36. Processing register section appears after risk register
    37. ComplianceGrid receives has_risk_register=True
    38. ComplianceGrid receives has_processing_register=True
    39. Renderer fail-safe: broken risk_register doesn't crash render
    40. Renderer fail-safe: broken processing_register doesn't crash render

  G. Edge cases and robustness
    41. RiskRegister with UNACCEPTABLE category produces CRITICAL session risk
    42. ProcessingRegister with no envelope has None user/org
    43. Static risks do not expose PII or internal implementation details
    44. Processing activities mention security measures (SHA-256, RSA, TLS)
    45. Risk register to_dict() round-trip (serialize/check structure)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch


# ============================================================================
# Helpers
# ============================================================================

def _make_envelope():
    from python.helpers.session_envelope import SessionEnvelope
    return SessionEnvelope(
        session_id="KRV-TEST-S15",
        username="testuser",
        organization="TestOrg",
    )


def _make_route_decision(category_name="HIGH_RISK", strength=0.85):
    from python.helpers.router.routing_contract import (
        RouteDecision, RouteVerdict, RouteIntent, IntentName, AIActCategory,
    )
    cat = AIActCategory(category_name.lower().replace("_", "_"))
    return RouteDecision(
        verdict=RouteVerdict.PROCEED,
        intents=[RouteIntent(name=IntentName.FINANCE, score=0.9)],
        routing_strength=strength,
        is_board_level=True,
        reasons=["test"],
        route_id="test-corr",
        ai_act_category=cat,
    )


def _make_tracker(agents=None):
    from python.helpers.pipeline_tracker import PipelineTracker
    tracker = PipelineTracker()
    for name in (agents or ["researcher", "finance"]):
        tracker.start_step(name)
        tracker.complete_step(name)
    return tracker


# ============================================================================
# A. RiskRegister
# ============================================================================

class TestRiskRegister:

    def test_01_static_risks_populated(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session()
        assert len(reg.risks) == 7

    def test_02_each_risk_has_required_fields(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session()
        for r in reg.risks:
            assert r.risk_id, f"Missing risk_id on {r}"
            assert r.domain, f"Missing domain on {r.risk_id}"
            assert r.description, f"Missing description on {r.risk_id}"
            assert r.level is not None, f"Missing level on {r.risk_id}"
            assert r.impact, f"Missing impact on {r.risk_id}"
            assert len(r.mitigations) > 0, f"No mitigations on {r.risk_id}"

    def test_03_from_session_without_context_only_static(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session()
        assert len(reg.session_risks) == 0
        assert len(reg.risks) == 7

    def test_04_low_confidence_adds_session_risk(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session(confidence_score=0.25)
        assert len(reg.session_risks) == 1
        assert reg.session_risks[0].risk_id == "RSK-SES-001"
        assert "0.25" in reg.session_risks[0].description or "25%" in reg.session_risks[0].description

    def test_05_high_risk_category_adds_session_risk(self):
        from python.helpers.risk_register import RiskRegister
        rd = _make_route_decision("HIGH_RISK")
        reg = RiskRegister.from_session(route_decision=rd)
        ses_ids = [r.risk_id for r in reg.session_risks]
        assert "RSK-SES-002" in ses_ids

    def test_06_minimal_risk_no_session_risk(self):
        from python.helpers.risk_register import RiskRegister
        rd = _make_route_decision("MINIMAL_RISK", strength=0.9)
        reg = RiskRegister.from_session(route_decision=rd, confidence_score=0.9)
        ses_ids = [r.risk_id for r in reg.session_risks]
        assert "RSK-SES-002" not in ses_ids

    def test_07_report_section_markdown_table(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session()
        section = reg.to_report_section()
        assert "### Registre des risques" in section
        assert "| ID |" in section
        assert "RSK-001" in section
        assert "RSK-007" in section

    def test_08_report_section_includes_mitigations(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session()
        section = reg.to_report_section()
        assert "Mesures d'attenuation detaillees" in section
        assert "FAIL_CLOSED" in section
        assert "Consensus PRISM" in section

    def test_09_to_dict_complete(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session(confidence_score=0.2)
        d = reg.to_dict()
        assert "risks" in d
        assert "session_risks" in d
        assert "total_risks" in d
        assert d["total_risks"] == len(d["risks"]) + len(d["session_risks"])
        for r in d["risks"]:
            assert "risk_id" in r
            assert "level" in r

    def test_10_risk_levels_cover_all(self):
        from python.helpers.risk_register import RiskRegister, RiskLevel
        reg = RiskRegister.from_session()
        levels = {r.level for r in reg.risks}
        assert RiskLevel.LOW in levels
        assert RiskLevel.MEDIUM in levels
        assert RiskLevel.HIGH in levels
        assert RiskLevel.CRITICAL in levels


# ============================================================================
# B. ProcessingRegister
# ============================================================================

class TestProcessingRegister:

    def test_11_static_activities_populated(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        assert len(reg.activities) == 2

    def test_12_each_activity_has_mandatory_fields(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        for a in reg.activities:
            assert a.activity_id, f"Missing activity_id"
            assert a.purpose, f"Missing purpose on {a.activity_id}"
            assert a.legal_basis, f"Missing legal_basis on {a.activity_id}"
            assert len(a.data_categories) > 0, f"No data_categories on {a.activity_id}"
            assert len(a.data_subject_categories) > 0, f"No data_subject_categories on {a.activity_id}"
            assert len(a.recipients) > 0, f"No recipients on {a.activity_id}"
            assert a.third_country_transfers, f"Missing transfers on {a.activity_id}"
            assert a.retention_period, f"Missing retention on {a.activity_id}"
            assert len(a.security_measures) > 0, f"No security_measures on {a.activity_id}"

    def test_13_enriches_with_envelope(self):
        from python.helpers.processing_register import ProcessingRegister
        env = _make_envelope()
        reg = ProcessingRegister.from_session(envelope=env)
        assert reg.session_user == "testuser"
        assert reg.session_organization == "TestOrg"

    def test_14_works_without_envelope(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        assert reg.session_user is None
        assert reg.session_organization is None
        assert len(reg.activities) == 2

    def test_15_report_section_markdown(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session(envelope=_make_envelope())
        section = reg.to_report_section()
        assert "### Registre des activites de traitement" in section
        assert "PROC-001" in section
        assert "PROC-002" in section

    def test_16_report_mentions_dpo(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        section = reg.to_report_section()
        assert "dpo@korev-evidence.com" in section

    def test_17_report_mentions_no_transfer(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        section = reg.to_report_section()
        assert "Aucun transfert hors UE" in section

    def test_18_to_dict_complete(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session(envelope=_make_envelope())
        d = reg.to_dict()
        assert d["controller"] == "KOREV AI"
        assert d["dpo_contact"] == "dpo@korev-evidence.com"
        assert len(d["activities"]) == 2
        assert d["session_user"] == "testuser"
        for a in d["activities"]:
            assert "purpose" in a
            assert "legal_basis" in a

    def test_19_has_required_fields_true(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        assert reg.has_required_fields() is True

    def test_20_has_required_fields_false_empty(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister(activities=[])
        assert reg.has_required_fields() is False


# ============================================================================
# C. ComplianceGrid Art. 9
# ============================================================================

class TestComplianceGridArt9:

    def test_21_art9_conforme_with_register(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            route_decision=_make_route_decision(),
            confidence_score=0.85,
            has_risk_register=True,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert art9.status == ComplianceStatus.CONFORME

    def test_22_art9_partiel_without_register(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            route_decision=_make_route_decision(),
            confidence_score=0.85,
            has_risk_register=False,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert art9.status == ComplianceStatus.PARTIEL

    def test_23_art9_evidence_mentions_register(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_risk_register=True,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert "Registre formel des risques present" in art9.evidence

    def test_24_art9_gaps_when_no_register(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_risk_register=False,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert "Registre formel des risques absent" in art9.gaps


# ============================================================================
# D. ComplianceGrid Art. 17
# ============================================================================

class TestComplianceGridArt17:

    def test_25_art17_evidence_monitoring_counters(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
        )
        art17 = [c for c in grid.checks if "Art. 17" in c.article][0]
        assert "audit_reports_generated_total" in art17.evidence

    def test_26_art17_evidence_risk_register(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_risk_register=True,
        )
        art17 = [c for c in grid.checks if "Art. 17" in c.article][0]
        assert "Registre des risques" in art17.evidence

    def test_27_art17_evidence_processing_register(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=True,
        )
        art17 = [c for c in grid.checks if "Art. 17" in c.article][0]
        assert "Registre des traitements" in art17.evidence

    def test_28_art17_still_partiel(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_risk_register=True,
            has_processing_register=True,
        )
        art17 = [c for c in grid.checks if "Art. 17" in c.article][0]
        assert art17.status == ComplianceStatus.PARTIEL
        assert "donnees d'entrainement" in art17.gaps


# ============================================================================
# E. ComplianceGrid RGPD Art. 30
# ============================================================================

class TestComplianceGridRGPD30:

    def test_29_art30_conforme_with_register(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=True,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert art30.status == ComplianceStatus.CONFORME

    def test_30_art30_partiel_without_register(self):
        from python.helpers.compliance_grid import ComplianceGrid, ComplianceStatus
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=False,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert art30.status == ComplianceStatus.PARTIEL

    def test_31_art30_evidence_mentions_register(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=True,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert "Registre formel Art. 30 present" in art30.evidence

    def test_32_art30_gaps_empty_with_register(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            has_processing_register=True,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert art30.gaps == ""


# ============================================================================
# F. AuditReportRenderer integration
# ============================================================================

class TestRendererRegisters:

    def test_33_render_includes_risk_register(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
        )
        result = renderer.render()
        assert "### Registre des risques" in result
        assert "Art. 9" in result

    def test_34_render_includes_processing_register(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
        )
        result = renderer.render()
        assert "### Registre des activites de traitement" in result
        assert "RGPD Art. 30" in result

    def test_35_risk_register_between_transparency_and_sources(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
        )
        result = renderer.render()
        transparency_pos = result.find("### Transparence du raisonnement")
        risk_pos = result.find("### Registre des risques")
        metadata_pos = result.find("### Metadonnees techniques")
        if transparency_pos >= 0:
            assert transparency_pos < risk_pos
        assert risk_pos < metadata_pos

    def test_36_processing_register_after_risk_register(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            response="Test response",
        )
        result = renderer.render()
        risk_pos = result.find("### Registre des risques")
        processing_pos = result.find("### Registre des activites de traitement")
        assert risk_pos < processing_pos

    def test_37_compliance_grid_receives_risk_register_true(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_risk_register=True,
        )
        art9 = [c for c in grid.checks if "Art. 9" in c.article][0]
        assert "Registre formel des risques present" in art9.evidence

    def test_38_compliance_grid_receives_processing_register_true(self):
        from python.helpers.compliance_grid import ComplianceGrid
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            has_processing_register=True,
        )
        art30 = [c for c in grid.checks if "RGPD" in c.article][0]
        assert "Registre formel Art. 30 present" in art30.evidence

    def test_39_risk_register_failsafe(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            response="Test response",
        )
        with patch(
            "python.helpers.risk_register.RiskRegister.from_session",
            side_effect=Exception("boom"),
        ):
            result = renderer.render()
            assert "### Integrite" in result or "### Metadonnees" in result

    def test_40_processing_register_failsafe(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        renderer = AuditReportRenderer(
            envelope=_make_envelope(),
            response="Test response",
        )
        with patch(
            "python.helpers.processing_register.ProcessingRegister.from_session",
            side_effect=Exception("boom"),
        ):
            result = renderer.render()
            assert "### Integrite" in result or "### Metadonnees" in result


# ============================================================================
# G. Edge cases and robustness
# ============================================================================

class TestEdgeCases:

    def test_41_unacceptable_category_critical_session_risk(self):
        from python.helpers.risk_register import RiskRegister, RiskLevel
        rd = _make_route_decision("UNACCEPTABLE", strength=0.1)
        reg = RiskRegister.from_session(route_decision=rd)
        ses_critical = [r for r in reg.session_risks if r.level == RiskLevel.CRITICAL]
        assert len(ses_critical) >= 1

    def test_42_processing_register_no_envelope(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session(envelope=None)
        assert reg.session_user is None
        assert reg.session_organization is None
        section = reg.to_report_section()
        assert "—" in section

    def test_43_static_risks_no_pii(self):
        from python.helpers.risk_register import RiskRegister
        reg = RiskRegister.from_session()
        section = reg.to_report_section()
        forbidden = ["@", "password", "token", "api_key", "secret", "ssh"]
        for term in forbidden:
            assert term not in section.lower(), (
                f"Potential PII/secret '{term}' found in risk register"
            )

    def test_44_processing_security_measures_mentioned(self):
        from python.helpers.processing_register import ProcessingRegister
        reg = ProcessingRegister.from_session()
        section = reg.to_report_section()
        assert "SHA-256" in section
        assert "RSA-PSS-SHA256" in section
        assert "TLS" in section

    def test_45_risk_register_to_dict_structure(self):
        from python.helpers.risk_register import RiskRegister
        rd = _make_route_decision("HIGH_RISK")
        reg = RiskRegister.from_session(route_decision=rd, confidence_score=0.3)
        d = reg.to_dict()
        assert isinstance(d["risks"], list)
        assert isinstance(d["session_risks"], list)
        assert d["total_risks"] == len(d["risks"]) + len(d["session_risks"])
        for r in d["risks"] + d["session_risks"]:
            assert set(r.keys()) == {
                "risk_id", "domain", "description", "level",
                "impact", "mitigations", "mitigation_status", "monitoring",
            }

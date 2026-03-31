"""
Tests unitaires SESSION 5 — ComplianceGrid

Couverture :
- ComplianceStatus enum
- ComplianceCheck dataclass et serialisation
- ComplianceGrid.evaluate() avec differents contextes
- Art. 13 : PARTIEL si session+tracker, NON_CONFORME si rien
- Art. 14 : PARTIEL toujours (mecanisme existe, registre absent)
- Art. 17 : PARTIEL toujours (logs oui, QMS complet non)
- Art. 9 : PARTIEL toujours (confidence oui, risk registry non)
- RGPD Art. 30 : PARTIEL si metadata, NON_CONFORME si vide
- overall_status : derive correct
- Honnetete : aucun check ne retourne CONFORME (anti-compliance-washing)
- to_report_table, to_dict
"""

import pytest
from unittest.mock import MagicMock, patch
from python.helpers.compliance_grid import (
    ComplianceStatus,
    ComplianceCheck,
    ComplianceGrid,
    _evaluate_art13_transparency,
    _evaluate_art14_human_supervision,
    _evaluate_art17_quality_system,
    _evaluate_art9_risk_management,
    _evaluate_rgpd_art30,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_envelope(**overrides):
    """Cree un mock SessionEnvelope."""
    envelope = MagicMock()
    envelope.session_id = overrides.get("session_id", "KRV-SES-20260331-ABC1234")
    envelope.started_at = overrides.get("started_at", "2026-03-31T10:00:00+00:00")
    envelope.completed_at = overrides.get("completed_at", "2026-03-31T10:05:00+00:00")
    envelope.integrity_hash = overrides.get("integrity_hash", "sha256:abc123")
    envelope.evidence_version = overrides.get("evidence_version", "3.0.0")
    envelope.username = overrides.get("username", "amine")
    envelope.organization = overrides.get("organization", "Korev AI")
    envelope.user_profile = overrides.get("user_profile", "Admin")
    return envelope


def _make_tracker(activated_count=3):
    """Cree un mock PipelineTracker."""
    tracker = MagicMock()
    activated = [MagicMock() for _ in range(activated_count)]
    tracker.get_activated.return_value = activated
    return tracker


def _make_route_decision():
    """Cree un mock RouteDecision avec classification."""
    rd = MagicMock()
    rd.ai_act_category = MagicMock()
    rd.ai_act_category.value = "limited_risk"
    rd.data_sensitivity = MagicMock()
    rd.data_sensitivity.value = "internal"
    return rd


# ═══════════════════════════════════════════════════════════════════════════════
# ComplianceStatus enum
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceStatus:
    def test_has_4_values(self):
        assert len(ComplianceStatus) == 4

    def test_values(self):
        assert ComplianceStatus.CONFORME.value == "conforme"
        assert ComplianceStatus.PARTIEL.value == "partiel"
        assert ComplianceStatus.NON_CONFORME.value == "non_conforme"
        assert ComplianceStatus.NON_APPLICABLE.value == "non_applicable"


# ═══════════════════════════════════════════════════════════════════════════════
# ComplianceCheck
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceCheck:
    def test_to_dict_without_gaps(self):
        check = ComplianceCheck(
            article="Art. 13",
            exigence="Transparence",
            status=ComplianceStatus.CONFORME,
            evidence="Traces presentes",
        )
        d = check.to_dict()
        assert d["article"] == "Art. 13"
        assert d["status"] == "conforme"
        assert "gaps" not in d

    def test_to_dict_with_gaps(self):
        check = ComplianceCheck(
            article="Art. 17",
            exigence="QMS",
            status=ComplianceStatus.PARTIEL,
            evidence="Logs structures",
            gaps="Monitoring absent",
        )
        d = check.to_dict()
        assert d["gaps"] == "Monitoring absent"


# ═══════════════════════════════════════════════════════════════════════════════
# Art. 13 — Transparence
# ═══════════════════════════════════════════════════════════════════════════════

class TestArt13Transparency:
    def test_partiel_with_session_and_tracker(self):
        check = _evaluate_art13_transparency(_make_envelope(), _make_tracker())
        assert check.status == ComplianceStatus.PARTIEL
        assert "Art. 13" in check.article
        assert "TraceStep" in check.evidence
        assert "COMPRENDRE" in check.gaps

    def test_non_conforme_without_anything(self):
        check = _evaluate_art13_transparency(None, None)
        assert check.status == ComplianceStatus.NON_CONFORME

    def test_evidence_mentions_session_id(self):
        check = _evaluate_art13_transparency(_make_envelope(), _make_tracker())
        assert "KRV-SES" in check.evidence

    def test_evidence_mentions_agent_count(self):
        check = _evaluate_art13_transparency(_make_envelope(), _make_tracker(5))
        assert "5 agent(s)" in check.evidence

    def test_evidence_mentions_integrity_hash(self):
        check = _evaluate_art13_transparency(_make_envelope(), _make_tracker())
        assert "SHA-256" in check.evidence

    def test_never_conforme(self):
        """Art. 13 ne peut pas etre CONFORME tant que l'export user n'est pas complet."""
        check = _evaluate_art13_transparency(_make_envelope(), _make_tracker(10))
        assert check.status != ComplianceStatus.CONFORME


# ═══════════════════════════════════════════════════════════════════════════════
# Art. 14 — Supervision humaine
# ═══════════════════════════════════════════════════════════════════════════════

class TestArt14HumanSupervision:
    def test_partiel_without_review(self):
        check = _evaluate_art14_human_supervision(_make_envelope())
        assert check.status == ComplianceStatus.PARTIEL
        assert "non declenchee" in check.gaps

    def test_partiel_with_review(self):
        check = _evaluate_art14_human_supervision(
            _make_envelope(), has_human_review_flag=True, human_reviewer="Dr. Martin"
        )
        assert check.status == ComplianceStatus.PARTIEL
        assert "Dr. Martin" in check.evidence
        assert "registre formel" in check.gaps.lower()

    def test_mechanism_always_mentioned(self):
        check = _evaluate_art14_human_supervision(None)
        assert "escalation" in check.evidence.lower()

    def test_never_conforme(self):
        check = _evaluate_art14_human_supervision(
            _make_envelope(), has_human_review_flag=True, human_reviewer="auditor"
        )
        assert check.status != ComplianceStatus.CONFORME


# ═══════════════════════════════════════════════════════════════════════════════
# Art. 17 — Systeme qualite
# ═══════════════════════════════════════════════════════════════════════════════

class TestArt17QualitySystem:
    def test_partiel_with_full_context(self):
        check = _evaluate_art17_quality_system(
            _make_envelope(), _make_tracker(), has_consensus=True
        )
        assert check.status == ComplianceStatus.PARTIEL
        assert "PRISM" in check.evidence
        assert "monitoring" in check.gaps.lower()

    def test_partiel_without_consensus(self):
        check = _evaluate_art17_quality_system(_make_envelope(), _make_tracker())
        assert check.status == ComplianceStatus.PARTIEL
        assert "PRISM" not in check.evidence

    def test_version_in_evidence_when_resolved(self):
        check = _evaluate_art17_quality_system(_make_envelope(evidence_version="3.0.0"), None)
        assert "3.0.0" in check.evidence

    def test_version_gap_when_unknown(self):
        check = _evaluate_art17_quality_system(
            _make_envelope(evidence_version="unknown"), None
        )
        assert "non resolue" in check.gaps.lower()

    def test_never_conforme(self):
        check = _evaluate_art17_quality_system(
            _make_envelope(), _make_tracker(), has_consensus=True
        )
        assert check.status != ComplianceStatus.CONFORME


# ═══════════════════════════════════════════════════════════════════════════════
# Art. 9 — Gestion des risques
# ═══════════════════════════════════════════════════════════════════════════════

class TestArt9RiskManagement:
    def test_partiel_with_confidence_and_route(self):
        check = _evaluate_art9_risk_management(
            _make_envelope(), _make_route_decision(), confidence_score=0.87
        )
        assert check.status == ComplianceStatus.PARTIEL
        assert "0.87" in check.evidence
        assert "limited_risk" in check.evidence
        assert "registre formel" in check.gaps.lower()

    def test_partiel_without_confidence(self):
        check = _evaluate_art9_risk_management(_make_envelope())
        assert check.status == ComplianceStatus.PARTIEL
        assert "CriticalityRouter" in check.evidence

    def test_partiel_without_route_decision(self):
        check = _evaluate_art9_risk_management(None, None, 0.95)
        assert check.status == ComplianceStatus.PARTIEL
        assert "0.95" in check.evidence

    def test_never_conforme(self):
        check = _evaluate_art9_risk_management(
            _make_envelope(), _make_route_decision(), 0.99
        )
        assert check.status != ComplianceStatus.CONFORME


# ═══════════════════════════════════════════════════════════════════════════════
# RGPD Art. 30 — Registre
# ═══════════════════════════════════════════════════════════════════════════════

class TestRGPDArt30:
    def test_partiel_with_metadata(self):
        check = _evaluate_rgpd_art30(_make_envelope())
        assert check.status == ComplianceStatus.PARTIEL
        assert "amine" in check.evidence
        assert "Korev AI" in check.evidence
        assert "finalites" in check.gaps.lower()

    def test_non_conforme_without_envelope(self):
        check = _evaluate_rgpd_art30(None)
        assert check.status == ComplianceStatus.NON_CONFORME

    def test_non_conforme_with_empty_envelope(self):
        empty = MagicMock()
        empty.username = None
        empty.organization = None
        empty.started_at = None
        empty.integrity_hash = None
        check = _evaluate_rgpd_art30(empty)
        assert check.status == ComplianceStatus.NON_CONFORME

    def test_never_conforme(self):
        check = _evaluate_rgpd_art30(_make_envelope())
        assert check.status != ComplianceStatus.CONFORME


# ═══════════════════════════════════════════════════════════════════════════════
# ComplianceGrid — Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceGrid:
    def test_evaluate_returns_5_checks(self):
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
        )
        assert len(grid.checks) == 5

    def test_all_articles_covered(self):
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        articles = {c.article for c in grid.checks}
        assert any("Art. 13" in a for a in articles)
        assert any("Art. 14" in a for a in articles)
        assert any("Art. 17" in a for a in articles)
        assert any("Art. 9" in a for a in articles)
        assert any("Art. 30" in a for a in articles)

    def test_overall_status_partiel_by_default(self):
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        assert grid.overall_status == ComplianceStatus.PARTIEL

    def test_overall_non_conforme_if_any_non_conforme(self):
        grid = ComplianceGrid.evaluate(envelope=None, tracker=None)
        assert grid.overall_status == ComplianceStatus.NON_CONFORME

    def test_summary_counts(self):
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        s = grid.summary
        assert "partiel" in s
        assert s.get("conforme", 0) == 0

    def test_no_check_is_conforme_anti_washing(self):
        """ANTI-COMPLIANCE-WASHING : aucun check ne doit etre CONFORME
        tant que les gaps documentes ne sont pas resolus."""
        grid = ComplianceGrid.evaluate(
            envelope=_make_envelope(),
            tracker=_make_tracker(),
            route_decision=_make_route_decision(),
            confidence_score=0.95,
            has_human_review=True,
            human_reviewer="Auditor",
            has_consensus=True,
        )
        for check in grid.checks:
            assert check.status != ComplianceStatus.CONFORME, (
                f"COMPLIANCE WASHING DETECTED: {check.article} marked CONFORME "
                f"but gaps exist: {check.gaps}"
            )

    def test_every_check_has_gaps(self):
        """Chaque check PARTIEL doit documenter ses gaps."""
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        for check in grid.checks:
            if check.status == ComplianceStatus.PARTIEL:
                assert check.gaps, f"{check.article} is PARTIEL but has no gaps documented"

    def test_to_report_table_contains_key_elements(self):
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        table = grid.to_report_table()
        assert "Grille de conformite" in table
        assert "Art. 13" in table
        assert "Partiel" in table
        assert "honnetement" in table.lower()

    def test_to_dict_structure(self):
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        d = grid.to_dict()
        assert "checks" in d
        assert "summary" in d
        assert "overall_status" in d
        assert len(d["checks"]) == 5
        assert d["overall_status"] == "partiel"

    def test_to_dict_json_serializable(self):
        import json
        grid = ComplianceGrid.evaluate(envelope=_make_envelope(), tracker=_make_tracker())
        serialized = json.dumps(grid.to_dict())
        assert '"article"' in serialized

    def test_evaluate_with_minimal_input(self):
        grid = ComplianceGrid.evaluate()
        assert len(grid.checks) == 5
        assert grid.overall_status in (ComplianceStatus.PARTIEL, ComplianceStatus.NON_CONFORME)

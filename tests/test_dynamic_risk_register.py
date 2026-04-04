"""
Tests A2A — Dynamic Risk Register.

Couvre :
  - Scoring de risque par session
  - Classification correcte (LOW / MEDIUM / HIGH / CRITICAL)
  - Declenchement correct des seuils HUMAN_REVIEW
  - Coherence des scores (monotonie, bornes)
  - Dashboard systeme agrege
  - Historisation (append-only log)
  - Scenarios d'echec (timeouts multiples, agents contradictoires)
  - Property tests (invariance a l'ordre, robustesse au bruit)
"""

import json
import os

import pytest

from python.helpers.dynamic_risk_register import (
    HUMAN_REVIEW_THRESHOLD,
    RISK_THRESHOLDS,
    RiskLevel,
    SessionRiskAssessment,
    SystemRiskDashboard,
    assess_session_risk,
    get_system_dashboard,
)


# ─── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def risk_dir(tmp_path):
    """Base directory for risk log storage."""
    return str(tmp_path)


def _assess(base_dir, **overrides):
    """Helper to create assessments with sensible defaults."""
    defaults = dict(
        context_id="ctx-risk-test",
        session_id="KRV-SES-TEST",
        consensus_achieved=True,
        consensus_rounds=1,
        confidence_score=0.85,
        error_count=0,
        timeout_count=0,
        delegation_depth=1,
        tool_call_count=2,
        execution_time_ms=5000,
        base_dir=base_dir,
    )
    defaults.update(overrides)
    return assess_session_risk(**defaults)


# ─── Risk Level Classification ────────────────────────────

class TestRiskClassification:
    def test_low_risk_normal_session(self, risk_dir):
        assessment = _assess(risk_dir)
        assert assessment.risk_level == RiskLevel.LOW.value
        assert assessment.risk_score < RISK_THRESHOLDS[RiskLevel.MEDIUM]
        assert assessment.requires_human_review is False

    def test_medium_risk_low_confidence(self, risk_dir):
        assessment = _assess(
            risk_dir,
            confidence_score=0.45,
            error_count=2,
            timeout_count=1,
        )
        assert assessment.risk_level in (RiskLevel.MEDIUM.value, RiskLevel.HIGH.value)
        assert assessment.risk_score >= RISK_THRESHOLDS[RiskLevel.MEDIUM]

    def test_high_risk_consensus_failure(self, risk_dir):
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            consensus_rounds=3,
            confidence_score=0.1,
            error_count=2,
            timeout_count=1,
        )
        assert assessment.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
        assert assessment.requires_human_review is True

    def test_critical_risk_multiple_failures(self, risk_dir):
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            consensus_rounds=3,
            confidence_score=0.1,
            error_count=3,
            timeout_count=2,
            execution_time_ms=150_000,
        )
        assert assessment.risk_level == RiskLevel.CRITICAL.value
        assert assessment.requires_human_review is True
        assert assessment.risk_score >= RISK_THRESHOLDS[RiskLevel.CRITICAL]


# ─── Human Review Threshold ──────────────────────────────

class TestHumanReviewThreshold:
    def test_low_does_not_trigger_review(self, risk_dir):
        assessment = _assess(risk_dir)
        assert assessment.requires_human_review is False

    def test_high_triggers_review(self, risk_dir):
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            confidence_score=0.2,
            error_count=2,
        )
        assert assessment.requires_human_review is True
        assert assessment.human_review_reason != ""

    def test_review_reason_includes_top_factors(self, risk_dir):
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            consensus_rounds=3,
            confidence_score=0.1,
        )
        if assessment.requires_human_review:
            assert "consensus_failure" in assessment.human_review_reason or \
                   "low_confidence" in assessment.human_review_reason


# ─── Score Coherence ──────────────────────────────────────

class TestScoreCoherence:
    def test_score_bounded_0_1(self, risk_dir):
        for confidence in [0.0, 0.1, 0.5, 0.9, 1.0]:
            for errors in [0, 1, 5, 10]:
                a = _assess(
                    risk_dir,
                    confidence_score=confidence,
                    error_count=errors,
                    context_id=f"ctx-{confidence}-{errors}",
                )
                assert 0.0 <= a.risk_score <= 1.0, \
                    f"Score {a.risk_score} out of bounds for conf={confidence}, err={errors}"

    def test_more_errors_higher_risk(self, risk_dir):
        a0 = _assess(risk_dir, error_count=0, context_id="ctx-e0")
        a3 = _assess(risk_dir, error_count=3, context_id="ctx-e3")
        assert a3.risk_score >= a0.risk_score

    def test_lower_confidence_higher_risk(self, risk_dir):
        a_high = _assess(risk_dir, confidence_score=0.95, context_id="ctx-ch")
        a_low = _assess(risk_dir, confidence_score=0.2, context_id="ctx-cl")
        assert a_low.risk_score >= a_high.risk_score

    def test_consensus_failure_increases_risk(self, risk_dir):
        a_ok = _assess(risk_dir, consensus_achieved=True, context_id="ctx-cok")
        a_fail = _assess(risk_dir, consensus_achieved=False, context_id="ctx-cfail")
        assert a_fail.risk_score > a_ok.risk_score


# ─── Risk Factors ─────────────────────────────────────────

class TestRiskFactors:
    def test_six_factors_always_present(self, risk_dir):
        assessment = _assess(risk_dir)
        assert len(assessment.factors) == 6

    def test_factor_weights_sum_to_one(self, risk_dir):
        assessment = _assess(risk_dir)
        total = sum(f.weight for f in assessment.factors)
        assert abs(total - 1.0) < 0.01

    def test_factor_names_are_unique(self, risk_dir):
        assessment = _assess(risk_dir)
        names = [f.name for f in assessment.factors]
        assert len(names) == len(set(names))

    def test_factor_normalized_values_bounded(self, risk_dir):
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            error_count=10,
            confidence_score=0.01,
        )
        for f in assessment.factors:
            assert 0.0 <= f.normalized_value <= 1.0, \
                f"Factor {f.name} normalized_value {f.normalized_value} out of bounds"


# ─── Dashboard ────────────────────────────────────────────

class TestSystemDashboard:
    def test_empty_dashboard(self, risk_dir):
        dashboard = get_system_dashboard(base_dir=risk_dir)
        assert dashboard.total_sessions == 0
        assert dashboard.average_risk_score == 0.0

    def test_dashboard_after_assessments(self, risk_dir):
        _assess(risk_dir, context_id="ctx-d1", confidence_score=0.9)
        _assess(risk_dir, context_id="ctx-d2", confidence_score=0.1,
                consensus_achieved=False)
        _assess(risk_dir, context_id="ctx-d3", confidence_score=0.5)

        dashboard = get_system_dashboard(base_dir=risk_dir)
        assert dashboard.total_sessions == 3
        assert dashboard.average_risk_score > 0
        assert dashboard.max_risk_score > 0
        assert len(dashboard.recent_assessments) == 3

    def test_dashboard_levels_count(self, risk_dir):
        _assess(risk_dir, context_id="ctx-low", confidence_score=0.95)
        _assess(risk_dir, context_id="ctx-high",
                consensus_achieved=False, confidence_score=0.1, error_count=3)

        dashboard = get_system_dashboard(base_dir=risk_dir)
        total_by_level = sum(dashboard.sessions_by_level.values())
        assert total_by_level == dashboard.total_sessions


# ─── Historization ────────────────────────────────────────

class TestHistorization:
    def test_append_only_log(self, risk_dir):
        _assess(risk_dir, context_id="ctx-h1")
        _assess(risk_dir, context_id="ctx-h2")
        _assess(risk_dir, context_id="ctx-h3")

        log_path = os.path.join(risk_dir, "tmp", "audit", "risk_register.jsonl")
        assert os.path.exists(log_path)

        with open(log_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 3

        for line in lines:
            entry = json.loads(line)
            assert "assessment_id" in entry
            assert "risk_score" in entry
            assert "risk_level" in entry

    def test_log_entries_are_ordered(self, risk_dir):
        for i in range(5):
            _assess(risk_dir, context_id=f"ctx-ord-{i}")

        log_path = os.path.join(risk_dir, "tmp", "audit", "risk_register.jsonl")
        with open(log_path) as f:
            entries = [json.loads(l) for l in f if l.strip()]

        timestamps = [e["assessed_at"] for e in entries]
        assert timestamps == sorted(timestamps)


# ─── Failure Scenarios ────────────────────────────────────

class TestFailureScenarios:
    def test_multiple_timeouts(self, risk_dir):
        """Scenario: 5 timeouts during execution."""
        assessment = _assess(
            risk_dir,
            timeout_count=5,
            error_count=2,
            confidence_score=0.4,
            context_id="ctx-timeout",
        )
        assert assessment.risk_score > RISK_THRESHOLDS[RiskLevel.MEDIUM]

    def test_contradictory_agents(self, risk_dir):
        """Scenario: agents disagree, consensus fails after 3 rounds."""
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            consensus_rounds=3,
            confidence_score=0.1,
            error_count=2,
            timeout_count=1,
            context_id="ctx-contradict",
        )
        assert assessment.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
        assert assessment.requires_human_review is True

    def test_corrupted_data_high_errors(self, risk_dir):
        """Scenario: multiple errors from corrupted input data."""
        assessment = _assess(
            risk_dir,
            error_count=5,
            confidence_score=0.2,
            context_id="ctx-corrupt",
        )
        assert assessment.risk_score > RISK_THRESHOLDS[RiskLevel.MEDIUM]

    def test_high_load_long_execution(self, risk_dir):
        """Scenario: execution under heavy load, >2min."""
        assessment = _assess(
            risk_dir,
            execution_time_ms=180_000,
            tool_call_count=25,
            delegation_depth=5,
            confidence_score=0.5,
            context_id="ctx-load",
        )
        assert assessment.risk_score > 0.15


# ─── Property Tests ───────────────────────────────────────

class TestProperties:
    def test_idempotent_scoring(self, risk_dir):
        """Property: same inputs always produce the same score."""
        kwargs = dict(
            context_id="ctx-idem",
            consensus_achieved=False,
            confidence_score=0.3,
            error_count=2,
            base_dir=risk_dir,
        )
        a1 = assess_session_risk(**kwargs)
        a2 = assess_session_risk(**kwargs)
        assert a1.risk_score == a2.risk_score
        assert a1.risk_level == a2.risk_level

    def test_monotonic_confidence(self, risk_dir):
        """Property: decreasing confidence → non-decreasing risk."""
        scores = []
        for conf in [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]:
            a = _assess(
                risk_dir,
                confidence_score=conf,
                context_id=f"ctx-mono-{conf}",
            )
            scores.append(a.risk_score)
        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], \
                f"Non-monotonic: conf decrease should increase risk, got {scores}"

    def test_assessment_id_uniqueness(self, risk_dir):
        """Property: all assessment IDs must be unique."""
        ids = set()
        for i in range(20):
            a = _assess(risk_dir, context_id=f"ctx-uniq-{i}")
            assert a.assessment_id not in ids, f"Duplicate ID: {a.assessment_id}"
            ids.add(a.assessment_id)

    def test_serialization_roundtrip(self, risk_dir):
        """Property: to_dict → from_dict preserves all fields."""
        assessment = _assess(
            risk_dir,
            consensus_achieved=False,
            confidence_score=0.25,
            error_count=2,
        )
        d = assessment.to_dict()
        restored = SessionRiskAssessment.from_dict(d)
        assert restored.risk_score == assessment.risk_score
        assert restored.risk_level == assessment.risk_level
        assert len(restored.factors) == len(assessment.factors)

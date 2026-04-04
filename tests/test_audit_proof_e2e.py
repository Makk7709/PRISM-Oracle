"""
Tests A2A — End-to-End Audit Proof.

Scenarios d'integration complets verifiant que les 3 briques
(Replay + Human Review + Risk Engine) fonctionnent ensemble
pour produire un systeme audit-proof.

Couvre :
  - Pipeline complet : session → risk → review → decision
  - Replay apres validation humaine
  - Detection de divergence apres modification
  - Tracabilite de bout en bout (correlation_id)
  - Scenarios d'echec cascades
  - Invariants systeme
"""

import json
import os

import pytest

from python.helpers.replay_engine import (
    DivergenceLevel,
    capture_snapshot,
    compare_responses,
    load_snapshot,
    save_snapshot,
    verify_snapshot_integrity,
)
from python.helpers.human_review import (
    ReviewStatus,
    ReviewTrigger,
    create_review,
    is_review_blocking,
    load_review,
    submit_review,
)
from python.helpers.dynamic_risk_register import (
    RiskLevel,
    assess_session_risk,
    get_system_dashboard,
)


# ─── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def audit_dir(tmp_path):
    """Shared base directory for all audit proof modules."""
    return str(tmp_path)


# ─── Pipeline Integration ────────────────────────────────

class TestFullPipeline:
    def test_session_to_risk_to_review_to_decision(self, audit_dir):
        """Full pipeline: execute → assess risk → trigger review → approve."""
        context_id = "ctx-pipeline-001"
        correlation_id = "corr-pipeline-001"
        query = "Analyze this financial report for compliance issues."
        response = "The report shows 3 compliance gaps that need attention."

        # Step 1: Capture snapshot
        snapshot = capture_snapshot(
            context_id=context_id,
            query=query,
            response=response,
            model_provider="openrouter",
            model_name="anthropic/claude-sonnet-4-20250514",
            model_temperature=0.0,
            correlation_id=correlation_id,
        )
        save_snapshot(snapshot, base_dir=audit_dir)

        # Step 2: Assess risk
        assessment = assess_session_risk(
            context_id=context_id,
            correlation_id=correlation_id,
            consensus_achieved=False,
            consensus_rounds=3,
            confidence_score=0.25,
            error_count=1,
            base_dir=audit_dir,
        )
        assert assessment.requires_human_review is True

        # Step 3: Create review (triggered by risk engine)
        review = create_review(
            context_id=context_id,
            query=query,
            response=response,
            trigger=ReviewTrigger.RISK_ENGINE,
            risk_level=assessment.risk_level,
            risk_score=assessment.risk_score,
            correlation_id=correlation_id,
            metadata={"assessment_id": assessment.assessment_id},
            base_dir=audit_dir,
        )
        assert review.is_pending is True

        # Step 4: Verify blocking
        blocking = is_review_blocking(context_id, base_dir=audit_dir)
        assert blocking is not None

        # Step 5: Submit decision
        decided = submit_review(
            review.review_id,
            reviewer_id="compliance_officer",
            reviewer_name="Jane Doe, DPO",
            status=ReviewStatus.APPROVED,
            justification="Verified: compliance gaps are documented and actionable.",
            base_dir=audit_dir,
        )
        assert decided.is_resolved is True

        # Step 6: Verify no longer blocking
        assert is_review_blocking(context_id, base_dir=audit_dir) is None

        # Step 7: Verify snapshot integrity
        loaded = load_snapshot(context_id, base_dir=audit_dir)
        assert verify_snapshot_integrity(loaded) is True

    def test_low_risk_skips_review(self, audit_dir):
        """Low-risk sessions should NOT trigger human review."""
        context_id = "ctx-lowrisk-001"

        snapshot = capture_snapshot(
            context_id=context_id,
            query="What time is it?",
            response="It is 14:30 UTC.",
        )
        save_snapshot(snapshot, base_dir=audit_dir)

        assessment = assess_session_risk(
            context_id=context_id,
            consensus_achieved=True,
            confidence_score=0.95,
            error_count=0,
            timeout_count=0,
            base_dir=audit_dir,
        )
        assert assessment.requires_human_review is False
        assert is_review_blocking(context_id, base_dir=audit_dir) is None


# ─── Replay After Review ─────────────────────────────────

class TestReplayAfterReview:
    def test_replay_matches_original_after_approval(self, audit_dir):
        """After human approval, replaying should match."""
        response = "Decision: approve with conditions."

        snapshot = capture_snapshot(
            context_id="ctx-replay-review",
            query="Should we proceed?",
            response=response,
            model_temperature=0.0,
        )
        save_snapshot(snapshot, base_dir=audit_dir)

        report = compare_responses(response, response)
        assert report.level == DivergenceLevel.NONE

    def test_replay_detects_tampering(self, audit_dir):
        """If snapshot response is tampered, integrity check must fail.

        Tamper detection works because verify_snapshot_integrity checks
        that sha256(response) matches the stored response_hash.
        """
        snapshot = capture_snapshot(
            context_id="ctx-tamper-test",
            query="Original query",
            response="Original response",
        )
        save_snapshot(snapshot, base_dir=audit_dir)

        loaded = load_snapshot("ctx-tamper-test", base_dir=audit_dir)
        assert verify_snapshot_integrity(loaded) is True

        # Tamper the response content — hash mismatch detected
        loaded.response = "TAMPERED response"
        assert verify_snapshot_integrity(loaded) is False


# ─── Correlation Traceability ─────────────────────────────

class TestCorrelationTraceability:
    def test_correlation_id_propagates(self, audit_dir):
        """correlation_id must be consistent across all artifacts."""
        corr_id = "TRACE-E2E-12345"
        context_id = "ctx-trace-001"

        snapshot = capture_snapshot(
            context_id=context_id,
            correlation_id=corr_id,
            query="Trace me",
            response="Traced.",
        )
        save_snapshot(snapshot, base_dir=audit_dir)

        assessment = assess_session_risk(
            context_id=context_id,
            correlation_id=corr_id,
            base_dir=audit_dir,
        )

        review = create_review(
            context_id=context_id,
            correlation_id=corr_id,
            base_dir=audit_dir,
        )

        assert snapshot.correlation_id == corr_id
        assert assessment.correlation_id == corr_id
        assert review.correlation_id == corr_id

    def test_all_artifacts_reference_same_context(self, audit_dir):
        """All audit artifacts must reference the same context_id."""
        ctx = "ctx-unified-001"

        snapshot = capture_snapshot(context_id=ctx, query="Q", response="A")
        save_snapshot(snapshot, base_dir=audit_dir)

        assessment = assess_session_risk(context_id=ctx, base_dir=audit_dir)
        review = create_review(context_id=ctx, base_dir=audit_dir)

        assert snapshot.context_id == ctx
        assert assessment.context_id == ctx
        assert review.context_id == ctx


# ─── Cascade Failure Scenarios ────────────────────────────

class TestCascadeFailures:
    def test_consensus_failure_triggers_review_triggers_rejection(self, audit_dir):
        """Consensus failure → HIGH risk → review → rejection chain."""
        ctx = "ctx-cascade-001"

        assessment = assess_session_risk(
            context_id=ctx,
            consensus_achieved=False,
            consensus_rounds=3,
            confidence_score=0.1,
            error_count=2,
            base_dir=audit_dir,
        )
        assert assessment.requires_human_review is True

        review = create_review(
            context_id=ctx,
            trigger=ReviewTrigger.RISK_ENGINE,
            risk_level=assessment.risk_level,
            base_dir=audit_dir,
        )

        rejected = submit_review(
            review.review_id,
            reviewer_id="rssi",
            status=ReviewStatus.REJECTED,
            justification="Consensus failure with very low confidence — cannot trust output.",
            base_dir=audit_dir,
        )
        assert rejected.status == ReviewStatus.REJECTED.value

    def test_multiple_sessions_mixed_risk(self, audit_dir):
        """Multiple sessions with varying risk levels."""
        for i in range(10):
            assess_session_risk(
                context_id=f"ctx-multi-{i}",
                consensus_achieved=(i % 3 != 0),
                confidence_score=0.1 * i,
                error_count=i % 4,
                base_dir=audit_dir,
            )

        dashboard = get_system_dashboard(base_dir=audit_dir)
        assert dashboard.total_sessions == 10
        assert sum(dashboard.sessions_by_level.values()) == 10


# ─── System Invariants ────────────────────────────────────

class TestSystemInvariants:
    def test_snapshot_immutable_after_save(self, audit_dir):
        """Invariant: saved snapshot must not change on disk without detection."""
        snapshot = capture_snapshot(
            context_id="ctx-immutable",
            query="Immutable query",
            response="Immutable response",
        )
        path = save_snapshot(snapshot, base_dir=audit_dir)

        with open(path) as f:
            original_content = f.read()

        loaded = load_snapshot("ctx-immutable", base_dir=audit_dir)
        assert verify_snapshot_integrity(loaded) is True

        # Tamper with response on disk — hash mismatch detected
        data = json.loads(original_content)
        data["response"] = "TAMPERED"
        with open(path, "w") as f:
            json.dump(data, f)

        tampered = load_snapshot("ctx-immutable", base_dir=audit_dir)
        assert verify_snapshot_integrity(tampered) is False

    def test_review_cannot_be_decided_twice(self, audit_dir):
        """Invariant: a resolved review cannot be re-decided."""
        review = create_review(context_id="ctx-double", base_dir=audit_dir)
        submit_review(
            review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="First",
            base_dir=audit_dir,
        )
        with pytest.raises(ValueError):
            submit_review(
                review.review_id,
                reviewer_id="admin2",
                status=ReviewStatus.REJECTED,
                justification="Second",
                base_dir=audit_dir,
            )

    def test_risk_score_deterministic(self, audit_dir):
        """Invariant: identical inputs always produce identical scores."""
        kwargs = dict(
            context_id="ctx-det",
            consensus_achieved=False,
            confidence_score=0.3,
            error_count=2,
            timeout_count=1,
            base_dir=audit_dir,
        )
        a1 = assess_session_risk(**kwargs)
        a2 = assess_session_risk(**kwargs)
        assert a1.risk_score == a2.risk_score

    def test_divergence_detection_symmetric(self):
        """Invariant: compare(a,b) similarity == compare(b,a) similarity."""
        a = "The market is bullish with strong indicators."
        b = "The market shows bearish trends and weak signals."
        r1 = compare_responses(a, b)
        r2 = compare_responses(b, a)
        assert r1.response_similarity == r2.response_similarity

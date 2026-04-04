"""
Tests de hardening — Corrections post-audit hostile.

Verifie que les failles detectees par l'audit hostile sont effectivement corrigees :
  - Path traversal dans review_id
  - Statuts invalides dans submit_review
  - Inputs negatifs / NaN dans le risk engine
  - context_id inclus dans l'integrite du snapshot
  - Validation des formats d'ID
"""

import math
import pytest

from python.helpers.replay_engine import (
    SessionSnapshot,
    capture_snapshot,
    verify_snapshot_integrity,
)
from python.helpers.human_review import (
    ReviewStatus,
    ReviewTrigger,
    create_review,
    load_review,
    submit_review,
)
from python.helpers.dynamic_risk_register import (
    RiskLevel,
    assess_session_risk,
)


# ─── Replay Engine Hardening ──────────────────────────────

class TestReplayHardening:
    def test_context_id_in_integrity_hash(self):
        """context_id must be protected by the integrity hash."""
        snap = capture_snapshot(
            context_id="ctx-original",
            query="test",
            response="test",
            correlation_id="fixed",
        )
        original_hash = snap.integrity_hash

        snap.context_id = "ctx-swapped"
        assert verify_snapshot_integrity(snap) is False
        assert snap.compute_integrity() != original_hash

    def test_history_hash_in_integrity(self):
        """history_hash must be protected by the integrity hash."""
        snap1 = capture_snapshot(
            context_id="ctx-hist",
            query="test",
            response="test",
            history_text="history A",
            correlation_id="fixed",
        )
        snap2 = capture_snapshot(
            context_id="ctx-hist",
            query="test",
            response="test",
            history_text="history B",
            correlation_id="fixed",
        )
        assert snap1.integrity_hash != snap2.integrity_hash


# ─── Human Review Hardening ───────────────────────────────

class TestHumanReviewHardening:
    def test_path_traversal_in_review_id_rejected(self, tmp_path):
        """review_id with path traversal chars must be rejected."""
        with pytest.raises(ValueError, match="Invalid review_id format"):
            load_review("../../../etc/passwd", base_dir=str(tmp_path))

    def test_slash_in_review_id_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid review_id format"):
            load_review("REV/../../evil", base_dir=str(tmp_path))

    def test_empty_review_id_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid review_id format"):
            load_review("", base_dir=str(tmp_path))

    def test_invalid_status_rejected(self, tmp_path):
        """Only APPROVED and REJECTED are valid terminal statuses."""
        base = str(tmp_path)
        rev = create_review(context_id="ctx-status", base_dir=base)

        with pytest.raises(ValueError, match="Invalid terminal status"):
            submit_review(
                rev.review_id,
                reviewer_id="admin",
                status=ReviewStatus.PENDING_REVIEW,
                justification="Try to re-set to pending",
                base_dir=base,
            )

    def test_expired_status_rejected(self, tmp_path):
        base = str(tmp_path)
        rev = create_review(context_id="ctx-expired", base_dir=base)

        with pytest.raises(ValueError, match="Invalid terminal status"):
            submit_review(
                rev.review_id,
                reviewer_id="admin",
                status=ReviewStatus.EXPIRED,
                justification="Try to expire",
                base_dir=base,
            )


# ─── Risk Engine Hardening ────────────────────────────────

class TestRiskEngineHardening:
    def test_negative_error_count_clamped(self, tmp_path):
        """Negative error_count must be clamped to 0."""
        base = str(tmp_path)
        a_neg = assess_session_risk(
            context_id="ctx-neg-err",
            error_count=-100,
            base_dir=base,
        )
        a_zero = assess_session_risk(
            context_id="ctx-zero-err",
            error_count=0,
            base_dir=base,
        )
        assert a_neg.risk_score == a_zero.risk_score

    def test_negative_timeout_count_clamped(self, tmp_path):
        """Negative timeout_count must be clamped to 0."""
        base = str(tmp_path)
        a_neg = assess_session_risk(
            context_id="ctx-neg-timeout",
            timeout_count=-50,
            base_dir=base,
        )
        a_zero = assess_session_risk(
            context_id="ctx-zero-timeout",
            timeout_count=0,
            base_dir=base,
        )
        assert a_neg.risk_score == a_zero.risk_score

    def test_nan_confidence_treated_as_unknown(self, tmp_path):
        """NaN confidence must be treated as unknown (0.5 risk)."""
        base = str(tmp_path)
        a_nan = assess_session_risk(
            context_id="ctx-nan-conf",
            confidence_score=float('nan'),
            base_dir=base,
        )
        a_none = assess_session_risk(
            context_id="ctx-none-conf",
            confidence_score=None,
            base_dir=base,
        )
        assert a_nan.risk_score == a_none.risk_score

    def test_inf_confidence_treated_as_unknown(self, tmp_path):
        """Inf confidence must be treated as unknown."""
        base = str(tmp_path)
        a_inf = assess_session_risk(
            context_id="ctx-inf-conf",
            confidence_score=float('inf'),
            base_dir=base,
        )
        a_none = assess_session_risk(
            context_id="ctx-none-conf2",
            confidence_score=None,
            base_dir=base,
        )
        assert a_inf.risk_score == a_none.risk_score

    def test_confidence_over_1_clamped(self, tmp_path):
        """confidence_score > 1.0 must be clamped to 1.0."""
        base = str(tmp_path)
        a_over = assess_session_risk(
            context_id="ctx-over-conf",
            confidence_score=5.0,
            base_dir=base,
        )
        a_one = assess_session_risk(
            context_id="ctx-one-conf",
            confidence_score=1.0,
            base_dir=base,
        )
        assert a_over.risk_score == a_one.risk_score

    def test_score_never_negative(self, tmp_path):
        """Risk score must always be >= 0."""
        base = str(tmp_path)
        for err in [-100, -1, 0, 1, 10]:
            for timeout in [-100, -1, 0, 1, 10]:
                a = assess_session_risk(
                    context_id=f"ctx-bound-{err}-{timeout}",
                    error_count=err,
                    timeout_count=timeout,
                    base_dir=base,
                )
                assert a.risk_score >= 0.0, \
                    f"Negative score {a.risk_score} for err={err}, timeout={timeout}"

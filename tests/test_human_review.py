"""
Tests A2A — Human Review Workflow.

Couvre :
  - Creation de reviews
  - Soumission de decisions (APPROVED / REJECTED)
  - Blocage sans validation
  - Passage apres validation
  - Rejet et justification
  - Audit trail (persistence des decisions)
  - Securite (double-soumission, review inexistant)
  - Property tests (idempotence, exhaustivite des etats)
"""

import json
import os

import pytest

from python.helpers.human_review import (
    ReviewDecision,
    ReviewRequest,
    ReviewStatus,
    ReviewTrigger,
    create_review,
    is_review_blocking,
    list_pending_reviews,
    load_review,
    submit_review,
)


# ─── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def review_dir(tmp_path):
    """Temporary directory for review storage."""
    reviews = tmp_path / "tmp" / "reviews"
    reviews.mkdir(parents=True)
    return str(tmp_path)


@pytest.fixture
def sample_review(review_dir):
    """Create a pending review for testing."""
    return create_review(
        context_id="ctx-test-001",
        session_id="KRV-SES-20260404-REVIEW1",
        query="Should we approve this high-risk transaction?",
        response="Based on analysis, the transaction appears legitimate.",
        trigger=ReviewTrigger.RISK_ENGINE,
        risk_level="HIGH",
        risk_score=0.75,
        username="test_user",
        organization="test_org",
        correlation_id="corr-rev-001",
        base_dir=review_dir,
    )


# ─── Review Creation ─────────────────────────────────────

class TestReviewCreation:
    def test_create_produces_valid_review(self, sample_review):
        assert sample_review.review_id.startswith("REV-")
        assert sample_review.context_id == "ctx-test-001"
        assert sample_review.status == ReviewStatus.PENDING_REVIEW.value
        assert sample_review.trigger == ReviewTrigger.RISK_ENGINE.value
        assert sample_review.risk_level == "HIGH"
        assert sample_review.risk_score == 0.75
        assert sample_review.response_hash.startswith("sha256:")

    def test_create_defaults(self, review_dir):
        rev = create_review(context_id="ctx-defaults", base_dir=review_dir)
        assert rev.status == ReviewStatus.PENDING_REVIEW.value
        assert rev.trigger == ReviewTrigger.MANUAL.value
        assert rev.risk_level == "UNKNOWN"
        assert rev.decision is None

    def test_create_persists_to_disk(self, sample_review, review_dir):
        path = os.path.join(review_dir, "tmp", "reviews", f"{sample_review.review_id}.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["review_id"] == sample_review.review_id

    def test_review_id_format(self, sample_review):
        parts = sample_review.review_id.split("-")
        assert parts[0] == "REV"
        assert len(parts[1]) == 8  # YYYYMMDD


# ─── Blocking Behavior ───────────────────────────────────

class TestBlocking:
    def test_pending_review_is_blocking(self, sample_review, review_dir):
        blocking = is_review_blocking("ctx-test-001", base_dir=review_dir)
        assert blocking is not None
        assert blocking.review_id == sample_review.review_id

    def test_no_review_is_not_blocking(self, review_dir):
        blocking = is_review_blocking("ctx-no-review", base_dir=review_dir)
        assert blocking is None

    def test_approved_review_is_not_blocking(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="Verified by senior analyst.",
            base_dir=review_dir,
        )
        blocking = is_review_blocking("ctx-test-001", base_dir=review_dir)
        assert blocking is None

    def test_rejected_review_is_not_blocking(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.REJECTED,
            justification="Transaction flagged as suspicious.",
            base_dir=review_dir,
        )
        blocking = is_review_blocking("ctx-test-001", base_dir=review_dir)
        assert blocking is None


# ─── Decision Submission ─────────────────────────────────

class TestDecisionSubmission:
    def test_approve_review(self, sample_review, review_dir):
        result = submit_review(
            sample_review.review_id,
            reviewer_id="admin_user",
            reviewer_name="Admin User",
            status=ReviewStatus.APPROVED,
            justification="Transaction verified against KYC records.",
            base_dir=review_dir,
        )
        assert result.status == ReviewStatus.APPROVED.value
        assert result.decision is not None
        assert result.decision.reviewer_id == "admin_user"
        assert result.decision.justification == "Transaction verified against KYC records."
        assert result.decision.decided_at != ""

    def test_reject_review(self, sample_review, review_dir):
        result = submit_review(
            sample_review.review_id,
            reviewer_id="compliance_officer",
            status=ReviewStatus.REJECTED,
            justification="Inconsistent with compliance policy CP-42.",
            base_dir=review_dir,
        )
        assert result.status == ReviewStatus.REJECTED.value
        assert result.is_resolved is True
        assert result.is_pending is False

    def test_approve_with_override(self, sample_review, review_dir):
        result = submit_review(
            sample_review.review_id,
            reviewer_id="senior_admin",
            status=ReviewStatus.APPROVED,
            justification="Override: manual correction of response.",
            override_response="The transaction is approved with conditions.",
            base_dir=review_dir,
        )
        assert result.decision.override_original is True
        assert result.decision.override_response == "The transaction is approved with conditions."

    def test_double_submission_raises(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="First decision.",
            base_dir=review_dir,
        )
        with pytest.raises(ValueError, match="already resolved"):
            submit_review(
                sample_review.review_id,
                reviewer_id="admin2",
                status=ReviewStatus.REJECTED,
                justification="Second attempt.",
                base_dir=review_dir,
            )

    def test_submit_nonexistent_raises(self, review_dir):
        with pytest.raises(ValueError, match="not found"):
            submit_review(
                "REV-00000000-BBBBBBBB",
                reviewer_id="admin",
                status=ReviewStatus.APPROVED,
                justification="N/A",
                base_dir=review_dir,
            )


# ─── Listing and Loading ─────────────────────────────────

class TestListingAndLoading:
    def test_list_pending_includes_new_review(self, sample_review, review_dir):
        pending = list_pending_reviews(base_dir=review_dir)
        assert len(pending) >= 1
        ids = [r.review_id for r in pending]
        assert sample_review.review_id in ids

    def test_list_pending_excludes_resolved(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="OK",
            base_dir=review_dir,
        )
        pending = list_pending_reviews(base_dir=review_dir)
        ids = [r.review_id for r in pending]
        assert sample_review.review_id not in ids

    def test_list_pending_filters_by_org(self, review_dir):
        create_review(
            context_id="ctx-org-a",
            organization="org_alpha",
            base_dir=review_dir,
        )
        create_review(
            context_id="ctx-org-b",
            organization="org_beta",
            base_dir=review_dir,
        )
        alpha = list_pending_reviews(organization="org_alpha", base_dir=review_dir)
        beta = list_pending_reviews(organization="org_beta", base_dir=review_dir)
        assert all(r.organization == "org_alpha" for r in alpha)
        assert all(r.organization == "org_beta" for r in beta)

    def test_load_review_roundtrip(self, sample_review, review_dir):
        loaded = load_review(sample_review.review_id, base_dir=review_dir)
        assert loaded is not None
        assert loaded.review_id == sample_review.review_id
        assert loaded.query == sample_review.query
        assert loaded.response_hash == sample_review.response_hash

    def test_load_nonexistent_returns_none(self, review_dir):
        assert load_review("REV-00000000-AAAAAAAA", base_dir=review_dir) is None


# ─── Audit Trail ──────────────────────────────────────────

class TestAuditTrail:
    def test_decision_persisted_with_full_metadata(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="dpo_user",
            reviewer_name="DPO Jane Doe",
            status=ReviewStatus.APPROVED,
            justification="Verified after manual investigation (ticket INC-1234).",
            base_dir=review_dir,
        )
        loaded = load_review(sample_review.review_id, base_dir=review_dir)
        assert loaded.decision.reviewer_id == "dpo_user"
        assert loaded.decision.reviewer_name == "DPO Jane Doe"
        assert "INC-1234" in loaded.decision.justification
        assert loaded.decision.decided_at != ""

    def test_review_preserves_original_data_after_decision(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="OK",
            base_dir=review_dir,
        )
        loaded = load_review(sample_review.review_id, base_dir=review_dir)
        assert loaded.query == "Should we approve this high-risk transaction?"
        assert loaded.risk_level == "HIGH"
        assert loaded.trigger == ReviewTrigger.RISK_ENGINE.value


# ─── Serialization ────────────────────────────────────────

class TestSerialization:
    def test_to_dict_roundtrip(self, sample_review, review_dir):
        d = sample_review.to_dict()
        restored = ReviewRequest.from_dict(d)
        assert restored.review_id == sample_review.review_id
        assert restored.status == sample_review.status

    def test_to_dict_with_decision(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="OK",
            base_dir=review_dir,
        )
        loaded = load_review(sample_review.review_id, base_dir=review_dir)
        d = loaded.to_dict()
        assert d["decision"]["reviewer_id"] == "admin"
        assert d["decision"]["status"] == "APPROVED"


# ─── Property Tests ───────────────────────────────────────

class TestProperties:
    def test_all_statuses_reachable(self, review_dir):
        """Property: every defined status must be reachable."""
        rev = create_review(context_id="ctx-states", base_dir=review_dir)
        assert rev.status == ReviewStatus.PENDING_REVIEW.value

        submitted = submit_review(
            rev.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="OK",
            base_dir=review_dir,
        )
        assert submitted.status == ReviewStatus.APPROVED.value

        rev2 = create_review(context_id="ctx-states-2", base_dir=review_dir)
        rejected = submit_review(
            rev2.review_id,
            reviewer_id="admin",
            status=ReviewStatus.REJECTED,
            justification="NO",
            base_dir=review_dir,
        )
        assert rejected.status == ReviewStatus.REJECTED.value

    def test_pending_is_not_resolved(self, sample_review):
        assert sample_review.is_pending is True
        assert sample_review.is_resolved is False

    def test_resolved_is_not_pending(self, sample_review, review_dir):
        submit_review(
            sample_review.review_id,
            reviewer_id="admin",
            status=ReviewStatus.APPROVED,
            justification="OK",
            base_dir=review_dir,
        )
        loaded = load_review(sample_review.review_id, base_dir=review_dir)
        assert loaded.is_pending is False
        assert loaded.is_resolved is True

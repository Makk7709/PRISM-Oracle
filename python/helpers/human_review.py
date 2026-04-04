"""
Human Review Workflow — validation humaine bloquante et tracable.

Implemente un mecanisme de review bloquant avec etats :
  PENDING_REVIEW → APPROVED | REJECTED

Chaque decision est journalisee avec identifiant reviewer, timestamp,
decision et justification pour conformite AI Act Art. 14.

Integration :
  - API /human_review pour gerer les reviews
  - Extension monologue_end verifie si un review est requis
  - DynamicRiskEngine declenche automatiquement sur HIGH/CRITICAL
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("human_review")


class ReviewStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ReviewTrigger(str, Enum):
    RISK_ENGINE = "RISK_ENGINE"
    MANUAL = "MANUAL"
    POLICY = "POLICY"
    CONSENSUS_FAILURE = "CONSENSUS_FAILURE"


@dataclass
class ReviewDecision:
    """Decision d'un reviewer humain."""
    reviewer_id: str = ""
    reviewer_name: str = ""
    decided_at: str = ""
    status: str = ReviewStatus.PENDING_REVIEW.value
    justification: str = ""
    override_original: bool = False
    override_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewRequest:
    """Demande de review humain pour une decision IA."""

    review_id: str = ""
    context_id: str = ""
    session_id: str = ""
    correlation_id: str = ""

    created_at: str = ""
    expires_at: Optional[str] = None
    status: str = ReviewStatus.PENDING_REVIEW.value

    trigger: str = ReviewTrigger.MANUAL.value
    risk_level: str = "UNKNOWN"
    risk_score: float = 0.0

    username: Optional[str] = None
    organization: Optional[str] = None
    agent_profile: str = "unknown"

    query: str = ""
    response: str = ""
    response_hash: str = ""

    decision: Optional[ReviewDecision] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.decision:
            d["decision"] = self.decision.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewRequest":
        dec_data = data.pop("decision", None)
        req = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if dec_data and isinstance(dec_data, dict):
            req.decision = ReviewDecision(**{
                k: v for k, v in dec_data.items()
                if k in ReviewDecision.__dataclass_fields__
            })
        return req

    @property
    def is_pending(self) -> bool:
        return self.status == ReviewStatus.PENDING_REVIEW.value

    @property
    def is_resolved(self) -> bool:
        return self.status in (
            ReviewStatus.APPROVED.value,
            ReviewStatus.REJECTED.value,
        )


_REVIEWS_DIR = "tmp/reviews"

_SAFE_ID_PATTERN = r'^REV-\d{8}-[A-Z0-9]{8}$'


def _validate_review_id(review_id: str) -> None:
    """Reject review_id values that could escape the storage directory."""
    import re
    if not review_id or not re.match(_SAFE_ID_PATTERN, review_id):
        raise ValueError(
            f"Invalid review_id format: {review_id!r}. "
            f"Expected: REV-YYYYMMDD-XXXXXXXX"
        )


def _reviews_dir(base_dir: str = "") -> str:
    if not base_dir:
        from python.helpers.files import get_base_dir
        base_dir = get_base_dir()
    d = os.path.join(base_dir, _REVIEWS_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def create_review(
    *,
    context_id: str,
    session_id: str = "",
    query: str = "",
    response: str = "",
    trigger: ReviewTrigger = ReviewTrigger.MANUAL,
    risk_level: str = "UNKNOWN",
    risk_score: float = 0.0,
    username: Optional[str] = None,
    organization: Optional[str] = None,
    agent_profile: str = "unknown",
    correlation_id: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    base_dir: str = "",
) -> ReviewRequest:
    """Cree une demande de review et la persiste."""
    import hashlib

    now = datetime.now(timezone.utc)
    review_id = f"REV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    req = ReviewRequest(
        review_id=review_id,
        context_id=context_id,
        session_id=session_id,
        correlation_id=correlation_id,
        created_at=now.isoformat(),
        status=ReviewStatus.PENDING_REVIEW.value,
        trigger=trigger.value,
        risk_level=risk_level,
        risk_score=risk_score,
        username=username,
        organization=organization,
        agent_profile=agent_profile,
        query=query,
        response=response,
        response_hash=(
            "sha256:" + hashlib.sha256(response.encode("utf-8")).hexdigest()
            if response else ""
        ),
        metadata=metadata or {},
    )

    _save_review(req, base_dir)

    try:
        from python.security.security_audit import log_security_event
        log_security_event(
            action="human_review_created",
            decision="pending",
            user=username,
            organization=organization,
            resource_type="review_request",
            resource_id=review_id,
            reason=f"trigger={trigger.value}, risk_level={risk_level}",
        )
    except Exception:
        pass

    try:
        from python.observability.runtime import ObservabilityMetrics
        ObservabilityMetrics.get().incr("human_reviews_created_total")
    except Exception:
        pass

    logger.info("Review created: %s (trigger=%s, risk=%s)", review_id, trigger.value, risk_level)
    return req


def submit_review(
    review_id: str,
    *,
    reviewer_id: str,
    reviewer_name: str = "",
    status: ReviewStatus,
    justification: str = "",
    override_response: str = "",
    base_dir: str = "",
) -> ReviewRequest:
    """Soumet une decision de review. Leve ValueError si le review n'existe pas.

    Seuls APPROVED et REJECTED sont des statuts terminaux valides.
    """
    if status not in (ReviewStatus.APPROVED, ReviewStatus.REJECTED):
        raise ValueError(
            f"Invalid terminal status: {status.value}. "
            f"Only APPROVED or REJECTED are allowed."
        )
    _validate_review_id(review_id)
    req = load_review(review_id, base_dir=base_dir)
    if req is None:
        raise ValueError(f"Review {review_id} not found")
    if req.is_resolved:
        raise ValueError(f"Review {review_id} already resolved: {req.status}")

    now = datetime.now(timezone.utc)
    req.status = status.value
    req.decision = ReviewDecision(
        reviewer_id=reviewer_id,
        reviewer_name=reviewer_name,
        decided_at=now.isoformat(),
        status=status.value,
        justification=justification,
        override_original=bool(override_response),
        override_response=override_response,
    )

    _save_review(req, base_dir)

    try:
        from python.security.security_audit import log_security_event
        log_security_event(
            action="human_review_decided",
            decision=status.value.lower(),
            user=req.username,
            organization=req.organization,
            resource_type="review_request",
            resource_id=review_id,
            reason=justification or "no justification provided",
            metadata={"reviewer_id": reviewer_id, "reviewer_name": reviewer_name},
        )
    except Exception:
        pass

    try:
        from python.observability.runtime import ObservabilityMetrics
        counter = (
            "human_reviews_approved_total"
            if status == ReviewStatus.APPROVED
            else "human_reviews_rejected_total"
        )
        ObservabilityMetrics.get().incr(counter)
    except Exception:
        pass

    logger.info("Review %s decided: %s by %s", review_id, status.value, reviewer_id)
    return req


def load_review(review_id: str, base_dir: str = "") -> Optional[ReviewRequest]:
    """Charge un review depuis le filesystem."""
    _validate_review_id(review_id)
    path = os.path.join(_reviews_dir(base_dir), f"{review_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return ReviewRequest.from_dict(json.load(f))


def list_pending_reviews(
    organization: Optional[str] = None,
    base_dir: str = "",
) -> List[ReviewRequest]:
    """Liste les reviews en attente, optionnellement filtres par org."""
    results = []
    d = _reviews_dir(base_dir)
    for fname in sorted(os.listdir(d)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(d, fname), "r", encoding="utf-8") as f:
            req = ReviewRequest.from_dict(json.load(f))
        if req.is_pending:
            if organization is None or req.organization == organization:
                results.append(req)
    return results


def is_review_blocking(context_id: str, base_dir: str = "") -> Optional[ReviewRequest]:
    """Verifie si un review bloquant est en attente pour ce contexte."""
    d = _reviews_dir(base_dir)
    for fname in sorted(os.listdir(d)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(d, fname), "r", encoding="utf-8") as f:
            req = ReviewRequest.from_dict(json.load(f))
        if req.context_id == context_id and req.is_pending:
            return req
    return None


def _save_review(req: ReviewRequest, base_dir: str = "") -> str:
    path = os.path.join(_reviews_dir(base_dir), f"{req.review_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(req.to_dict(), f, ensure_ascii=False, indent=2)
    return path

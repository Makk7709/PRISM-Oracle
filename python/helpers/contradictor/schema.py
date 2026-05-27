# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              CONTRADICTOR — Strict output schema & internal model            ║
║                                                                              ║
║  Defines the JSON contract returned by the Contradictor Agent and the        ║
║  internal `ContradictorReview` data structure consumed by the orchestrator.  ║
║                                                                              ║
║  DESIGN PRINCIPLES                                                           ║
║  - dataclass + enum: aligned with the existing convention used by            ║
║    `python/helpers/router/routing_contract.py` (no new Pydantic dep).        ║
║  - Strict validation: missing field, wrong enum, wrong type, out-of-range    ║
║    confidence are ALL rejected.                                              ║
║  - No silent coercion. Either the payload conforms or `validate_contradictor_output`
║    returns errors and `output=None`.                                         ║
║  - Deterministic hashing for audit traceability.                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ContradictorVerdict(str, Enum):
    """Strict verdict enum for the contradictor."""

    CHALLENGE = "challenge"
    NO_MAJOR_OBJECTION = "no_major_objection"


class ContradictorRiskLevel(str, Enum):
    """Risk level reported by the contradictor."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictorStatus(str, Enum):
    """Lifecycle status of a contradictor invocation."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    SCHEMA_FAIL = "schema_fail"
    ERROR = "error"
    SKIPPED = "skipped"


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT MODEL (LLM contract)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ContradictorOutput:
    """
    Schema of the JSON payload the Contradictor Agent MUST produce.

    Failure to conform => `validate_contradictor_output` returns errors and
    the orchestrator records `status=schema_fail`.
    """

    verdict: ContradictorVerdict
    risk_level: ContradictorRiskLevel
    contradictions: List[str]
    missing_evidence: List[str]
    failure_modes: List[str]
    legal_or_audit_risks: List[str]
    recommended_adjustments: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "risk_level": self.risk_level.value,
            "contradictions": list(self.contradictions),
            "missing_evidence": list(self.missing_evidence),
            "failure_modes": list(self.failure_modes),
            "legal_or_audit_risks": list(self.legal_or_audit_risks),
            "recommended_adjustments": list(self.recommended_adjustments),
            "confidence": round(float(self.confidence), 4),
        }


@dataclass
class ContradictorReview:
    """
    Internal model carried through the pipeline.

    Holds the strict output (when status=success) plus lifecycle metadata
    suitable for audit logs.
    """

    status: ContradictorStatus
    correlation_id: str
    output: Optional[ContradictorOutput] = None
    latency_ms: Optional[int] = None
    schema_errors: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def risk_level(self) -> Optional[ContradictorRiskLevel]:
        return self.output.risk_level if self.output else None

    @property
    def verdict(self) -> Optional[ContradictorVerdict]:
        return self.output.verdict if self.output else None

    @property
    def confidence(self) -> Optional[float]:
        return self.output.confidence if self.output else None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "status": self.status.value,
            "correlation_id": self.correlation_id,
            "latency_ms": self.latency_ms,
            "schema_errors": list(self.schema_errors),
            "error_message": self.error_message,
        }
        if self.output is not None:
            d["output"] = self.output.to_dict()
        else:
            d["output"] = None
        return d

    def output_hash(self) -> str:
        """Deterministic hash of the output payload (or status if no output)."""
        if self.output is None:
            payload = {"status": self.status.value, "error": self.error_message or ""}
        else:
            payload = self.output.to_dict()
        canon = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIRED FIELDS
# ═══════════════════════════════════════════════════════════════════════════════


REQUIRED_FIELDS: Tuple[str, ...] = (
    "verdict",
    "risk_level",
    "contradictions",
    "missing_evidence",
    "failure_modes",
    "legal_or_audit_risks",
    "recommended_adjustments",
    "confidence",
)


LIST_FIELDS: Tuple[str, ...] = (
    "contradictions",
    "missing_evidence",
    "failure_modes",
    "legal_or_audit_risks",
    "recommended_adjustments",
)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


def validate_contradictor_output(
    payload: Any,
) -> Tuple[Optional[ContradictorOutput], List[str]]:
    """
    Strictly validate a contradictor payload.

    Args:
        payload: Decoded JSON object (must be a dict).

    Returns:
        (output, errors).
        - On success: (ContradictorOutput, []).
        - On failure: (None, ["..."]) with each issue described.
    """
    errors: List[str] = []

    if not isinstance(payload, dict):
        return None, [f"payload must be a JSON object, got {type(payload).__name__}"]

    for field_name in REQUIRED_FIELDS:
        if field_name not in payload:
            errors.append(f"missing required field: {field_name}")

    if errors:
        return None, errors

    verdict_raw = payload.get("verdict")
    try:
        verdict = ContradictorVerdict(verdict_raw)
    except (ValueError, TypeError):
        allowed = ", ".join(v.value for v in ContradictorVerdict)
        errors.append(
            f"invalid verdict: {verdict_raw!r} (allowed: {allowed})"
        )
        verdict = None  # type: ignore[assignment]

    risk_raw = payload.get("risk_level")
    try:
        risk_level = ContradictorRiskLevel(risk_raw)
    except (ValueError, TypeError):
        allowed = ", ".join(v.value for v in ContradictorRiskLevel)
        errors.append(
            f"invalid risk_level: {risk_raw!r} (allowed: {allowed})"
        )
        risk_level = None  # type: ignore[assignment]

    for list_field in LIST_FIELDS:
        value = payload.get(list_field)
        if not isinstance(value, list):
            errors.append(
                f"{list_field} must be a list of strings, got {type(value).__name__}"
            )
            continue
        for idx, item in enumerate(value):
            if not isinstance(item, str):
                errors.append(
                    f"{list_field}[{idx}] must be a string, got {type(item).__name__}"
                )

    confidence_raw = payload.get("confidence")
    if not isinstance(confidence_raw, (int, float)) or isinstance(confidence_raw, bool):
        errors.append(
            f"confidence must be a float in [0.0, 1.0], got {type(confidence_raw).__name__}"
        )
        confidence: Optional[float] = None
    else:
        confidence = float(confidence_raw)
        if confidence < 0.0 or confidence > 1.0:
            errors.append(
                f"confidence must be in [0.0, 1.0], got {confidence}"
            )
            confidence = None

    if errors:
        return None, errors

    assert verdict is not None
    assert risk_level is not None
    assert confidence is not None

    output = ContradictorOutput(
        verdict=verdict,
        risk_level=risk_level,
        contradictions=[str(x) for x in payload["contradictions"]],
        missing_evidence=[str(x) for x in payload["missing_evidence"]],
        failure_modes=[str(x) for x in payload["failure_modes"]],
        legal_or_audit_risks=[str(x) for x in payload["legal_or_audit_risks"]],
        recommended_adjustments=[str(x) for x in payload["recommended_adjustments"]],
        confidence=confidence,
    )
    return output, []


# ═══════════════════════════════════════════════════════════════════════════════
# HUMAN-REVIEW RULE
# ═══════════════════════════════════════════════════════════════════════════════


HUMAN_REVIEW_RISK_LEVELS = frozenset({ContradictorRiskLevel.HIGH, ContradictorRiskLevel.CRITICAL})

HUMAN_REVIEW_FAILURE_STATUSES = frozenset(
    {ContradictorStatus.TIMEOUT, ContradictorStatus.SCHEMA_FAIL, ContradictorStatus.ERROR}
)


def is_human_review_required(review: ContradictorReview, *, was_required: bool) -> bool:
    """
    Decide whether human review is required given a ContradictorReview.

    Rule (governed, no auto-veto):
        - If the contradictor reports risk_level in {high, critical} => True.
        - If the contradictor was required but the run failed
          (timeout, schema_fail, error) => True (fail-safe escalation).
        - Otherwise => False.
    """
    if review.output is not None and review.output.risk_level in HUMAN_REVIEW_RISK_LEVELS:
        return True
    if was_required and review.status in HUMAN_REVIEW_FAILURE_STATUSES:
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════


__all__ = [
    "ContradictorVerdict",
    "ContradictorRiskLevel",
    "ContradictorStatus",
    "ContradictorOutput",
    "ContradictorReview",
    "validate_contradictor_output",
    "is_human_review_required",
    "REQUIRED_FIELDS",
    "LIST_FIELDS",
    "HUMAN_REVIEW_RISK_LEVELS",
    "HUMAN_REVIEW_FAILURE_STATUSES",
]

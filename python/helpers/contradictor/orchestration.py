# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          CONTRADICTOR — Orchestration glue: consume RouteDecision flag       ║
║                                                                              ║
║  This is THE consumer of `RouteDecision.requires_contradictor`.              ║
║                                                                              ║
║  The router DECIDES (`requires_contradictor=True/False`).                    ║
║  The orchestrator EXECUTES (this module) by deciding whether to invoke the   ║
║  contradictor LLM, validating its output, and producing audit-grade          ║
║  structured logs and a `human_review_required` boolean.                      ║
║                                                                              ║
║  Single entry point: `process_contradictor_for_response`.                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from python.helpers.router.routing_contract import RouteDecision
from python.helpers.contradictor.invoker import (
    LLMCallable,
    invoke_contradictor,
    skipped_review,
)
from python.helpers.contradictor.profile_mapping import resolve_profile_for_intent
from python.helpers.contradictor.schema import (
    ContradictorReview,
    ContradictorStatus,
    is_human_review_required,
)

logger = logging.getLogger("contradictor_orchestration")


# ═══════════════════════════════════════════════════════════════════════════════
# HASHING UTILITIES (audit-grade, no PII)
# ═══════════════════════════════════════════════════════════════════════════════


def _stable_hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def _route_decision_hash(decision: RouteDecision) -> str:
    """
    Deterministic short hash of the relevant routing context.

    Reuses the dataclass's compute_hash() to stay consistent with router's
    snapshot testing.
    """
    return decision.compute_hash()


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════════


def build_audit_log(
    *,
    route_decision: RouteDecision,
    review: ContradictorReview,
    human_review_required: bool,
    user_question: str,
    agent_response: str,
    contradictor_profile: str,
) -> Dict[str, Any]:
    """
    Build the structured audit dict for this contradictor cycle.

    No raw PII: questions and responses are hashed.
    """
    output_dict = review.output.to_dict() if review.output else None
    return {
        "correlation_id": review.correlation_id,
        "requires_contradictor": bool(route_decision.requires_contradictor),
        "contradictor_invoked": review.status != ContradictorStatus.SKIPPED,
        "contradictor_status": review.status.value,
        "contradictor_latency_ms": review.latency_ms,
        "contradictor_verdict": review.output.verdict.value if review.output else None,
        "contradictor_risk_level": review.output.risk_level.value if review.output else None,
        "contradictor_confidence": review.output.confidence if review.output else None,
        "contradictor_profile": contradictor_profile,
        "contradictor_schema_errors": list(review.schema_errors),
        "contradictor_error_message": review.error_message,
        "human_review_required": bool(human_review_required),
        # Hashed payloads — no PII in audit logs
        "input_hash": _stable_hash(user_question),
        "output_hash": review.output_hash(),
        "route_decision_hash": _route_decision_hash(route_decision),
        # Convenience snapshot of the validated payload (already non-PII per contract)
        "contradictor_output": output_dict,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION LOG
# ═══════════════════════════════════════════════════════════════════════════════


def _log_decision(audit: Dict[str, Any]) -> None:
    logger.info(
        "[CONTRADICTOR] decision | correlation_id=%s | required=%s | invoked=%s | "
        "status=%s | risk=%s | verdict=%s | human_review=%s | latency_ms=%s | "
        "input_hash=%s | output_hash=%s | route_hash=%s",
        audit["correlation_id"],
        audit["requires_contradictor"],
        audit["contradictor_invoked"],
        audit["contradictor_status"],
        audit["contradictor_risk_level"],
        audit["contradictor_verdict"],
        audit["human_review_required"],
        audit["contradictor_latency_ms"],
        audit["input_hash"],
        audit["output_hash"],
        audit["route_decision_hash"],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


async def process_contradictor_for_response(
    *,
    route_decision: RouteDecision,
    user_question: str,
    agent_response: str,
    correlation_id: str,
    llm_callable: Optional[LLMCallable] = None,
    timeout_ms: int = 20_000,
) -> Tuple[ContradictorReview, bool, Dict[str, Any]]:
    """
    Consume `route_decision.requires_contradictor` and, if true, invoke the
    contradictor agent on `agent_response`. Otherwise return a skipped review.

    Returns:
        (review, human_review_required, audit_log_dict)
    """
    contradictor_profile = resolve_profile_for_intent("contradictor")

    if not route_decision.requires_contradictor:
        review = skipped_review(correlation_id)
        human_review = is_human_review_required(review, was_required=False)
        audit = build_audit_log(
            route_decision=route_decision,
            review=review,
            human_review_required=human_review,
            user_question=user_question,
            agent_response=agent_response,
            contradictor_profile=contradictor_profile,
        )
        _log_decision(audit)
        return review, human_review, audit

    review = await invoke_contradictor(
        user_question=user_question,
        agent_response=agent_response,
        route_decision=route_decision.to_dict(),
        correlation_id=correlation_id,
        llm_callable=llm_callable,
        timeout_ms=timeout_ms,
    )
    human_review = is_human_review_required(review, was_required=True)
    audit = build_audit_log(
        route_decision=route_decision,
        review=review,
        human_review_required=human_review,
        user_question=user_question,
        agent_response=agent_response,
        contradictor_profile=contradictor_profile,
    )
    _log_decision(audit)
    return review, human_review, audit


__all__ = [
    "build_audit_log",
    "process_contradictor_for_response",
]

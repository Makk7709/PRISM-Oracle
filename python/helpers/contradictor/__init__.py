# -*- coding: utf-8 -*-
"""
Contradictor — Hostile review agent for board-level multi-intent decisions.

Public surface:
    - schema.py         : strict JSON contract + internal models
    - invoker.py        : single-turn LLM call producing a ContradictorReview
    - orchestration.py  : consumer of RouteDecision.requires_contradictor
    - profile_mapping.py: canonical application-side intent->profile map

See agents/contradictor/_context.md for the agent profile prompt.
See docs/audits/CONTRADICTOR_AGENT_HOSTILE_AUDIT.md for the audit trail.
"""
from __future__ import annotations

from python.helpers.contradictor.schema import (
    ContradictorOutput,
    ContradictorReview,
    ContradictorRiskLevel,
    ContradictorStatus,
    ContradictorVerdict,
    HUMAN_REVIEW_FAILURE_STATUSES,
    HUMAN_REVIEW_RISK_LEVELS,
    LIST_FIELDS,
    REQUIRED_FIELDS,
    is_human_review_required,
    validate_contradictor_output,
)
from python.helpers.contradictor.invoker import (
    CONTRADICTOR_PROMPT_TEMPLATE,
    LLMCallable,
    build_contradictor_prompt,
    invoke_contradictor,
    parse_contradictor_response,
    skipped_review,
)
from python.helpers.contradictor.orchestration import (
    build_audit_log,
    process_contradictor_for_response,
)
from python.helpers.contradictor.profile_mapping import (
    INTENT_TO_PROFILE,
    resolve_profile_for_intent,
)


__all__ = [
    # Schema
    "ContradictorVerdict",
    "ContradictorRiskLevel",
    "ContradictorStatus",
    "ContradictorOutput",
    "ContradictorReview",
    "REQUIRED_FIELDS",
    "LIST_FIELDS",
    "HUMAN_REVIEW_RISK_LEVELS",
    "HUMAN_REVIEW_FAILURE_STATUSES",
    "validate_contradictor_output",
    "is_human_review_required",
    # Invoker
    "CONTRADICTOR_PROMPT_TEMPLATE",
    "LLMCallable",
    "build_contradictor_prompt",
    "parse_contradictor_response",
    "invoke_contradictor",
    "skipped_review",
    # Orchestration
    "build_audit_log",
    "process_contradictor_for_response",
    # Profile mapping
    "INTENT_TO_PROFILE",
    "resolve_profile_for_intent",
]

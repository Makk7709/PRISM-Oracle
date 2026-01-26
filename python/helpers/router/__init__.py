"""
Deterministic Router — Policy-driven multi-intent routing.

This module provides:
- Deterministic routing (no LLM judgment)
- Multi-intent detection with weighted keywords
- Board-level triggers for strategic requests
- Anti-injection protection
- Strict contracts for all outputs

Usage:
    from python.helpers.router import decide_route, RouteDecision
    
    decision = decide_route("Analyse financière du deal M&A avec risques juridiques")
    
    if decision.verdict == RouteVerdict.PROCEED:
        for intent in decision.intents:
            print(f"  - {intent.name.value}: {intent.score:.2f}")
    
    if decision.is_board_level:
        print("Board-level request detected!")

Feature Flag:
    Set DETERMINISTIC_ROUTER=1 to enable deterministic routing in multitask.
    Default: falls back to LLM-based routing.
"""

import os

# Contracts
from .routing_contract import (
    # Enums
    RouteVerdict,
    IntentName,
    ConfidenceLevel,
    AgentVerdict,
    RiskSeverity,
    # Contracts
    RouteIntent,
    RouteDecision,
    AgentResult,
    AgentRisk,
    AgentAssumption,
    AgentArtifact,
    # Validation
    validate_route_decision,
    validate_agent_result,
)

# Policy
from .policy import (
    Keyword,
    IntentPolicy,
    MultiIntentRule,
    INTENT_POLICIES,
    BOARD_LEVEL_KEYWORDS,
    BOARD_LEVEL_THRESHOLD,
    BOARD_LEVEL_CORE_INTENTS,
    MULTI_INTENT_RULES,
    INJECTION_PATTERNS,
    POLICY_VERSION,
)

# Router
from .router import (
    decide_route,
    get_primary_intent,
    should_involve_legal,
    is_board_level_request,
    _canonicalize_text,
    _stable_route_id,
    _stable_input_hash,
)

# Judge (when available)
try:
    from .judge import (
        JudgeVerdict,
        JudgeResult,
        judge_step,
    )
except ImportError:
    # Judge not yet implemented
    pass


def is_deterministic_router_enabled() -> bool:
    """
    Check if deterministic router is enabled via feature flag.
    
    Environment variables (any of these enables the router):
    - DETERMINISTIC_ROUTER_V2=1
    - DETERMINISTIC_ROUTER=1
    
    Returns:
        True if deterministic routing is enabled, False otherwise.
    """
    return (
        os.environ.get("DETERMINISTIC_ROUTER_V2", "0") == "1" or
        os.environ.get("DETERMINISTIC_ROUTER", "0") == "1"
    )


__all__ = [
    # Feature flag
    "is_deterministic_router_enabled",
    # Contracts
    "RouteVerdict",
    "IntentName",
    "ConfidenceLevel",
    "AgentVerdict",
    "RiskSeverity",
    "RouteIntent",
    "RouteDecision",
    "AgentResult",
    "AgentRisk",
    "AgentAssumption",
    "AgentArtifact",
    "validate_route_decision",
    "validate_agent_result",
    # Policy
    "Keyword",
    "IntentPolicy",
    "MultiIntentRule",
    "INTENT_POLICIES",
    "BOARD_LEVEL_KEYWORDS",
    "BOARD_LEVEL_THRESHOLD",
    "BOARD_LEVEL_CORE_INTENTS",
    "MULTI_INTENT_RULES",
    "INJECTION_PATTERNS",
    "POLICY_VERSION",
    # Router
    "decide_route",
    "get_primary_intent",
    "should_involve_legal",
    "is_board_level_request",
    # Testing helpers
    "_canonicalize_text",
    "_stable_route_id",
    "_stable_input_hash",
]

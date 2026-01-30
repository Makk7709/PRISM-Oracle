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
    # Strategic documents
    STRATEGIC_DOCUMENT_KEYWORDS,
    STRATEGIC_DOCUMENT_THRESHOLD,
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

# Legal Pipeline Integration
try:
    from ..legal_pipeline import (
        LegalRiskTier,
        DecisionScope,
        Jurisdiction,
        LegalRouteContext,
        detect_legal_context,
    )
    LEGAL_PIPELINE_AVAILABLE = True
except ImportError:
    LEGAL_PIPELINE_AVAILABLE = False
    LegalRiskTier = None
    DecisionScope = None
    Jurisdiction = None
    LegalRouteContext = None
    detect_legal_context = None

# Metrics
from .metrics import RouterMetrics, RouterStats, DivergenceSample

# Strategic Pipeline Integration
try:
    from ..strategic_pipeline import (
        StrategicRouteContext,
        StrategicPipelineResult,
        detect_strategic_context,
        enrich_route_decision,
        validate_strategic_response,
        run_strategic_pipeline,
        should_enforce_strategic_validation,
        get_strategic_requirements_summary,
    )
    STRATEGIC_PIPELINE_AVAILABLE = True
except ImportError:
    STRATEGIC_PIPELINE_AVAILABLE = False
    StrategicRouteContext = None
    StrategicPipelineResult = None
    detect_strategic_context = None
    enrich_route_decision = None
    validate_strategic_response = None
    run_strategic_pipeline = None
    should_enforce_strategic_validation = None
    get_strategic_requirements_summary = None


def is_deterministic_router_enabled() -> bool:
    """
    Check if deterministic router is enabled via feature flag.
    
    Levels:
        0 = OFF (default)
        1 = Audit-only (log + metrics, no behavioral change)
        2 = Enforcement soft (block high-stakes if router says REFUSE/CLARIFY)
        3 = Enforcement hard (replace LLM routing entirely)
    
    Environment variables:
    - DETERMINISTIC_ROUTER_V2=1|2|3
    - DETERMINISTIC_ROUTER=1 (legacy, maps to level 1)
    
    Returns:
        True if deterministic routing is enabled (level >= 1), False otherwise.
    """
    level = os.environ.get("DETERMINISTIC_ROUTER_V2", "0")
    return level in ("1", "2", "3") or os.environ.get("DETERMINISTIC_ROUTER", "0") == "1"


def get_enforcement_level() -> int:
    """
    Get the current enforcement level (0-3).
    
    Returns:
        0: OFF
        1: Audit-only
        2: Enforcement soft
        3: Enforcement hard
    """
    try:
        level = int(os.environ.get("DETERMINISTIC_ROUTER_V2", "0"))
        return min(max(level, 0), 3)  # Clamp to 0-3
    except ValueError:
        return 0


__all__ = [
    # Feature flag
    "is_deterministic_router_enabled",
    "get_enforcement_level",
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
    # Strategic documents
    "STRATEGIC_DOCUMENT_KEYWORDS",
    "STRATEGIC_DOCUMENT_THRESHOLD",
    # Router
    "decide_route",
    "get_primary_intent",
    "should_involve_legal",
    "is_board_level_request",
    # Metrics
    "RouterMetrics",
    "RouterStats",
    "DivergenceSample",
    # Testing helpers
    "_canonicalize_text",
    "_stable_route_id",
    "_stable_input_hash",
    # Legal Pipeline
    "LEGAL_PIPELINE_AVAILABLE",
    "LegalRiskTier",
    "DecisionScope",
    "Jurisdiction",
    "LegalRouteContext",
    "detect_legal_context",
    # Strategic Pipeline
    "STRATEGIC_PIPELINE_AVAILABLE",
    "StrategicRouteContext",
    "StrategicPipelineResult",
    "detect_strategic_context",
    "enrich_route_decision",
    "validate_strategic_response",
    "run_strategic_pipeline",
    "should_enforce_strategic_validation",
    "get_strategic_requirements_summary",
]

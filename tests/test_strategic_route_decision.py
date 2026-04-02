"""
SESSION 11 — Tests: RouteDecision persistence from strategic pipeline.

Validates that _persist_route_decision() builds a correct RouteDecision
from StrategicResult + StrategicDetection, covering:
  - ai_act_category derivation from mobilised agents
  - routing_strength calculation from source count + validation
  - Serialisation round-trip (to_dict / from_dict)
  - Fallback when no responses match known profiles
  - Edge case: FAIL_CLOSED (validation_passed=False)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional
from unittest.mock import MagicMock

from python.helpers.router.routing_contract import (
    RouteDecision,
    RouteIntent,
    RouteVerdict,
    IntentName,
    AIActCategory,
    ConfidenceLevel,
)
from python.helpers.strategic_orchestrator import (
    AgentResponse,
    StrategicDetection,
    StrategicResult,
)


def _make_detection(doc_type="market_study", min_sources=10):
    return StrategicDetection(
        is_strategic=True,
        document_type=doc_type,
        required_agents=["researcher", "finance", "marketing", "sales"],
        min_sources=min_sources,
    )


def _make_result(
    responses: Optional[List[AgentResponse]] = None,
    total_sources: int = 50,
    validation_passed: bool = True,
):
    if responses is None:
        responses = [
            AgentResponse("Agent-R", "researcher", "...", 30, 200, True),
            AgentResponse("Agent-F", "finance", "...", 10, 300, True),
            AgentResponse("Agent-M", "marketing", "...", 5, 150, True),
            AgentResponse("Agent-S", "sales", "...", 5, 100, True),
        ]
    return StrategicResult(
        success=True,
        document_type="market_study",
        responses=responses,
        consolidated_response="consolidated text",
        total_sources=total_sources,
        validation_passed=validation_passed,
        correlation_id="test-corr-id",
        duration_ms=1000,
    )


def _make_hook():
    """Build a minimal StrategicEnforcementMonologueHook with a mock agent."""
    from python.extensions.monologue_start._15_strategic_enforcement import (
        StrategicEnforcementMonologueHook,
    )
    agent = MagicMock()
    stored = {}
    agent.set_data = lambda k, v: stored.__setitem__(k, v)
    agent.get_data = lambda k: stored.get(k)
    hook = StrategicEnforcementMonologueHook.__new__(StrategicEnforcementMonologueHook)
    hook.agent = agent
    hook._stored = stored
    return hook


class TestRouteDecisionPersistence:

    def test_basic_persist(self):
        """RouteDecision is stored as _route_decision_v2 with correct fields."""
        hook = _make_hook()
        result = _make_result()
        detection = _make_detection()

        hook._persist_route_decision(result, detection, "corr-001")

        raw = hook._stored.get("_route_decision_v2")
        assert raw is not None
        rd = RouteDecision.from_dict(raw)
        assert rd.verdict == RouteVerdict.PROCEED
        assert rd.is_board_level is True
        assert rd.route_id == "corr-001"

    def test_ai_act_category_derived_from_finance(self):
        """Finance intent -> HIGH_RISK via INTENT_TO_AI_ACT mapping."""
        hook = _make_hook()
        result = _make_result()
        detection = _make_detection()

        hook._persist_route_decision(result, detection, "corr-002")

        raw = hook._stored["_route_decision_v2"]
        rd = RouteDecision.from_dict(raw)
        assert rd.ai_act_category == AIActCategory.HIGH_RISK

    def test_routing_strength_high_sources(self):
        """50 sources / 10 min -> ratio 1.0, + 0.2 validation = capped at 1.0."""
        hook = _make_hook()
        result = _make_result(total_sources=50, validation_passed=True)
        detection = _make_detection(min_sources=10)

        hook._persist_route_decision(result, detection, "corr-003")

        rd = RouteDecision.from_dict(hook._stored["_route_decision_v2"])
        assert rd.routing_strength == 1.0
        assert rd.confidence_level == ConfidenceLevel.HIGH

    def test_routing_strength_partial_sources(self):
        """5 sources / 10 min -> ratio 0.5 -> 0.5*0.8 = 0.4, + 0.2 = 0.6."""
        hook = _make_hook()
        result = _make_result(total_sources=5, validation_passed=True)
        detection = _make_detection(min_sources=10)

        hook._persist_route_decision(result, detection, "corr-004")

        rd = RouteDecision.from_dict(hook._stored["_route_decision_v2"])
        assert rd.routing_strength == 0.6
        assert rd.confidence_level == ConfidenceLevel.MEDIUM

    def test_fail_closed_no_validation_bonus(self):
        """validation_passed=False -> no +0.2 bonus."""
        hook = _make_hook()
        result = _make_result(total_sources=10, validation_passed=False)
        detection = _make_detection(min_sources=10)

        hook._persist_route_decision(result, detection, "corr-005")

        rd = RouteDecision.from_dict(hook._stored["_route_decision_v2"])
        assert rd.routing_strength == 0.8
        assert "FAIL_CLOSED" in rd.reasons[1]

    def test_failed_agent_gets_low_score(self):
        """A failed agent response should get score 0.2 instead of 1.0."""
        hook = _make_hook()
        responses = [
            AgentResponse("R", "researcher", "ok", 20, 100, True),
            AgentResponse("F", "finance", "", 0, 50, False, error="timeout"),
        ]
        result = _make_result(responses=responses, total_sources=20)
        detection = _make_detection(min_sources=10)

        hook._persist_route_decision(result, detection, "corr-006")

        rd = RouteDecision.from_dict(hook._stored["_route_decision_v2"])
        intent_scores = {i.name: i.score for i in rd.intents}
        assert intent_scores[IntentName.RESEARCHER] == 1.0
        assert intent_scores[IntentName.FINANCE] == 0.2

    def test_fallback_when_no_known_profile(self):
        """Unknown profiles -> fallback RESEARCHER intent."""
        hook = _make_hook()
        responses = [
            AgentResponse("X", "unknown_profile", "...", 10, 100, True),
        ]
        result = _make_result(responses=responses, total_sources=10)
        detection = _make_detection(min_sources=10)

        hook._persist_route_decision(result, detection, "corr-007")

        rd = RouteDecision.from_dict(hook._stored["_route_decision_v2"])
        assert len(rd.intents) == 1
        assert rd.intents[0].name == IntentName.RESEARCHER

    def test_round_trip_serialization(self):
        """to_dict -> from_dict preserves all key fields."""
        hook = _make_hook()
        result = _make_result()
        detection = _make_detection()

        hook._persist_route_decision(result, detection, "corr-008")

        raw = hook._stored["_route_decision_v2"]
        rd1 = RouteDecision.from_dict(raw)
        rd2 = RouteDecision.from_dict(rd1.to_dict())

        assert rd1.verdict == rd2.verdict
        assert rd1.routing_strength == rd2.routing_strength
        assert rd1.ai_act_category == rd2.ai_act_category
        assert rd1.is_board_level == rd2.is_board_level
        assert len(rd1.intents) == len(rd2.intents)

    def test_non_blocking_on_internal_error(self):
        """Internal errors are swallowed — _route_decision_v2 is NOT set."""
        hook = _make_hook()
        result = MagicMock()
        result.responses = "not_iterable_will_crash"
        result.total_sources = 10
        result.validation_passed = True
        detection = _make_detection()

        hook._persist_route_decision(result, detection, "corr-009")
        assert "_route_decision_v2" not in hook._stored

    def test_zero_sources_gives_zero_strength(self):
        """0 sources + no validation -> strength = 0.0."""
        hook = _make_hook()
        result = _make_result(total_sources=0, validation_passed=False)
        detection = _make_detection(min_sources=10)

        hook._persist_route_decision(result, detection, "corr-010")

        rd = RouteDecision.from_dict(hook._stored["_route_decision_v2"])
        assert rd.routing_strength == 0.0
        assert rd.confidence_level == ConfidenceLevel.LOW

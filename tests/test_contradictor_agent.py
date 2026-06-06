# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
TESTS — Contradictor Agent (TDD STRICT)
═══════════════════════════════════════════════════════════════════════════════

These tests verify that the dead architectural signal `requires_contradictor`
is now consumed by the application pipeline:

    flag computed -> flag consumed -> agent invoked -> output validated
    -> audit logs -> human review if needed.

Tests cover (per audit specification):
  1. Invocation when requires_contradictor=True
  2. Board-level multi-intent triggers the full invocation chain
  3. Strategic pipeline forces and consumes the flag
  4. No invocation when requires_contradictor=False
  5. Strict JSON schema validation
  6. risk_level=high|critical => human_review_required=True
  7. Timeout => contradictor_status="timeout", audited, not silent
  8. Invalid JSON => schema_fail, audited, never injected
  9. Audit trace contains all required structured fields
 10. Application profile mapping never falls back to "default"

No real LLM calls. The LLM is injected as a `llm_callable` to test the
orchestration deterministically. The network guard in `tests/conftest.py`
prevents real LiteLLM calls regardless.

This file is the RED specification: it MUST fail before the implementation
of `python/helpers/contradictor/` is committed, and MUST pass after.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python.helpers.router import (
    IntentName,
    RouteDecision,
    RouteIntent,
    RouteVerdict,
    decide_route,
)
from python.helpers.router.routing_contract import (
    AIActCategory,
    DataSensitivity,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures: route decisions
# ═══════════════════════════════════════════════════════════════════════════════


def _make_route_decision(
    *,
    requires_contradictor: bool,
    is_board_level: bool = True,
    intents: Optional[list] = None,
) -> RouteDecision:
    """Build a synthetic RouteDecision for tests."""
    if intents is None:
        intents = [
            RouteIntent(
                name=IntentName.FINANCE,
                score=0.85,
                matched_keywords=["ebitda", "valorisation"],
                is_required=True,
                reason="finance score 8.5",
            ),
            RouteIntent(
                name=IntentName.LEGAL_SAFE,
                score=0.72,
                matched_keywords=["cession", "garantie"],
                is_required=True,
                reason="legal score 7.2",
            ),
        ]
    return RouteDecision(
        verdict=RouteVerdict.PROCEED,
        intents=intents,
        routing_strength=0.82,
        is_board_level=is_board_level,
        requires_contradictor=requires_contradictor,
        reasons=["test-fixture"],
        policy_version="1.0.0",
        route_id="test-route",
        input_hash="testhash1234",
        ai_act_category=AIActCategory.HIGH_RISK,
        data_sensitivity=DataSensitivity.CONFIDENTIAL,
    )


def _valid_contradictor_payload(
    *,
    verdict: str = "challenge",
    risk_level: str = "medium",
    confidence: float = 0.7,
) -> dict:
    """Build a valid contradictor JSON payload."""
    return {
        "verdict": verdict,
        "risk_level": risk_level,
        "contradictions": ["DCF assume une croissance lineaire non justifiee."],
        "missing_evidence": ["pas de benchmark sectoriel cite"],
        "failure_modes": ["valorisation surevaluee si marche se retracte"],
        "legal_or_audit_risks": ["pas de mention des garanties de passif"],
        "recommended_adjustments": [
            "ajouter analyse de sensibilite",
            "documenter hypotheses de marche",
        ],
        "confidence": confidence,
    }


def _make_llm_callable(payload: dict | str) -> Callable[[str], Awaitable[str]]:
    """Create an async LLM-like callable returning the given payload as JSON text."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    async def _call(prompt: str) -> str:
        return text

    return _call


# ═══════════════════════════════════════════════════════════════════════════════
# Imports of the SUT — these MUST fail initially (RED).
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def contradictor_module():
    """Import the contradictor module. Will fail in RED phase."""
    from python.helpers import contradictor as mod  # noqa: F401

    return mod


@pytest.fixture(scope="module")
def orchestration_module():
    from python.helpers.contradictor import orchestration as mod  # noqa: F401

    return mod


@pytest.fixture(scope="module")
def schema_module():
    from python.helpers.contradictor import schema as mod  # noqa: F401

    return mod


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: requires_contradictor=True triggers invocation
# ═══════════════════════════════════════════════════════════════════════════════


class TestRequiresContradictorInvocation:
    @pytest.mark.asyncio
    async def test_requires_contradictor_triggers_contradictor_agent_invocation(
        self, orchestration_module
    ):
        """When RouteDecision.requires_contradictor=True the orchestrator MUST
        call invoke_contradictor exactly once. No silent fallback to default."""
        from python.helpers.contradictor import schema as cs

        decision = _make_route_decision(requires_contradictor=True)

        llm_calls: list[str] = []

        async def spy_llm(prompt: str) -> str:
            llm_calls.append(prompt)
            return json.dumps(_valid_contradictor_payload())

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="Faut-il accepter le LBO propose par le repreneur ?",
            agent_response="Oui, le LBO est interessant.",
            correlation_id="cid-test-1",
            llm_callable=spy_llm,
        )

        assert review.status == cs.ContradictorStatus.SUCCESS, (
            "Expected status=success when LLM returns valid payload"
        )
        assert len(llm_calls) == 1, (
            "invoke_contradictor MUST call LLM exactly once when required"
        )
        # No silent fallback to default profile.
        assert audit["contradictor_invoked"] is True
        assert audit["contradictor_profile"] == "contradictor"
        assert audit["contradictor_profile"] != "default"

    @pytest.mark.asyncio
    async def test_contradictor_invoked_callable_observes_route_context(
        self, orchestration_module
    ):
        """The contradictor LLM prompt MUST include the route decision context
        (board-level signal, intents) so the review is grounded."""
        decision = _make_route_decision(requires_contradictor=True)

        observed_prompts: list[str] = []

        async def spy_llm(prompt: str) -> str:
            observed_prompts.append(prompt)
            return json.dumps(_valid_contradictor_payload())

        await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="LBO 50M chez ALPHA SAS",
            agent_response="recommandation positive",
            correlation_id="cid-ctx",
            llm_callable=spy_llm,
        )

        assert len(observed_prompts) == 1
        prompt = observed_prompts[0]
        # Prompt MUST mention key route context so the reviewer can act hostilely.
        assert "finance" in prompt.lower()
        assert "legal" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Board-level multi-intent end-to-end through the router
# ═══════════════════════════════════════════════════════════════════════════════


class TestBoardLevelMultiIntentRoutesToContradictor:
    @pytest.mark.asyncio
    async def test_board_level_multi_intent_routes_to_contradictor_review(
        self, orchestration_module
    ):
        """Board-level multi-intent request -> requires_contradictor=True ->
        contradictor agent invoked -> structured review returned."""
        # Real router call with a board-level multi-intent prompt that
        # triggers the M&A/LBO board-level keywords AND finance + legal_safe.
        decision = decide_route(
            "M&A LBO sur la filiale alpha: due diligence financiere (EBITDA, "
            "valorisation) et clauses juridiques (cession, garantie de passif)"
        )

        assert decision.is_board_level, "router should flag this as board-level"
        assert len(decision.intents) >= 2, "router should detect multi-intent"
        assert decision.requires_contradictor, (
            "router MUST set requires_contradictor for board-level multi-intent"
        )

        async def fake_llm(prompt: str) -> str:
            return json.dumps(_valid_contradictor_payload(risk_level="high"))

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="Decision strategique cession filiale",
            agent_response="cession recommandee",
            correlation_id="cid-board",
            llm_callable=fake_llm,
        )

        from python.helpers.contradictor import schema as cs

        assert review.status == cs.ContradictorStatus.SUCCESS
        assert review.output is not None
        assert review.output.risk_level == cs.ContradictorRiskLevel.HIGH
        assert human_review is True, "high risk MUST trigger human review"
        assert audit["contradictor_invoked"] is True
        assert audit["requires_contradictor"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Strategic pipeline forces AND the orchestrator consumes the flag
# ═══════════════════════════════════════════════════════════════════════════════


class TestStrategicPipelineForcesAndConsumesContradictor:
    @pytest.mark.asyncio
    async def test_strategic_pipeline_forces_and_consumes_contradictor(
        self, orchestration_module
    ):
        """When strategic_pipeline.enrich_route_decision forces
        requires_contradictor=True, the orchestrator MUST consume it."""
        from python.helpers.strategic_pipeline import (
            StrategicRouteContext,
            enrich_route_decision,
        )
        from python.helpers.strategic_contract import (
            StrategicDocumentType,
            Criticality,
        )

        # Base decision without contradictor
        base = _make_route_decision(requires_contradictor=False)
        context = StrategicRouteContext(
            is_strategic=True,
            document_types=[StrategicDocumentType.MARKET_STUDY],
            criticality=Criticality.HIGH,
            required_agents=["finance", "researcher"],
        )

        enriched = enrich_route_decision(base, context)
        assert enriched.requires_contradictor is True, (
            "strategic pipeline MUST force requires_contradictor for >=2 intents"
        )

        async def fake_llm(prompt: str) -> str:
            return json.dumps(_valid_contradictor_payload())

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=enriched,
            user_question="etude de marche",
            agent_response="analyse marche",
            correlation_id="cid-strat",
            llm_callable=fake_llm,
        )

        from python.helpers.contradictor import schema as cs

        assert review.status == cs.ContradictorStatus.SUCCESS
        assert audit["contradictor_invoked"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: No invocation when not required
# ═══════════════════════════════════════════════════════════════════════════════


class TestContradictorNotInvokedWhenNotRequired:
    @pytest.mark.asyncio
    async def test_contradictor_not_invoked_when_not_required(
        self, orchestration_module
    ):
        """When RouteDecision.requires_contradictor=False, the orchestrator
        MUST NOT invoke the contradictor LLM at all."""
        decision = _make_route_decision(requires_contradictor=False, is_board_level=False)

        call_count = 0

        async def spy_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return "{}"

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="petite question",
            agent_response="reponse simple",
            correlation_id="cid-noreq",
            llm_callable=spy_llm,
        )

        from python.helpers.contradictor import schema as cs

        assert call_count == 0, "LLM MUST NOT be called when not required"
        assert review.status == cs.ContradictorStatus.SKIPPED
        assert review.output is None
        assert human_review is False
        assert audit["contradictor_invoked"] is False
        assert audit["contradictor_status"] == "skipped"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Strict schema validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestContradictorOutputSchemaStrictValidation:
    def test_contradictor_output_schema_strict_validation(self, schema_module):
        """The schema MUST reject any payload missing required fields, with
        an out-of-enum value, with a non-list field, or confidence outside [0,1]."""
        cs = schema_module

        # Valid case
        valid = _valid_contradictor_payload()
        output, errors = cs.validate_contradictor_output(valid)
        assert output is not None
        assert errors == []
        assert output.verdict == cs.ContradictorVerdict.CHALLENGE
        assert output.risk_level == cs.ContradictorRiskLevel.MEDIUM
        assert 0.0 <= output.confidence <= 1.0

        # Missing required field
        bad = dict(valid)
        bad.pop("risk_level")
        output, errors = cs.validate_contradictor_output(bad)
        assert output is None
        assert any("risk_level" in e for e in errors)

        # Wrong enum
        bad = dict(valid, verdict="approve")
        output, errors = cs.validate_contradictor_output(bad)
        assert output is None
        assert any("verdict" in e for e in errors)

        # Wrong type for list field
        bad = dict(valid, contradictions="not a list")
        output, errors = cs.validate_contradictor_output(bad)
        assert output is None
        assert any("contradictions" in e for e in errors)

        # Confidence out of bounds
        bad = dict(valid, confidence=1.5)
        output, errors = cs.validate_contradictor_output(bad)
        assert output is None
        assert any("confidence" in e for e in errors)

        bad = dict(valid, confidence=-0.1)
        output, errors = cs.validate_contradictor_output(bad)
        assert output is None
        assert any("confidence" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: High/Critical risk triggers human_review_required
# ═══════════════════════════════════════════════════════════════════════════════


class TestHighOrCriticalRiskRequiresHumanReview:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("risk_level", ["high", "critical"])
    async def test_high_or_critical_contradictor_risk_requires_human_review(
        self, orchestration_module, risk_level
    ):
        """When the contradictor reports risk_level high/critical, the
        orchestration MUST flag human_review_required=True (consumable,
        not a mere log)."""
        decision = _make_route_decision(requires_contradictor=True)

        async def fake_llm(prompt: str) -> str:
            return json.dumps(_valid_contradictor_payload(risk_level=risk_level))

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="board decision",
            agent_response="recommendation",
            correlation_id=f"cid-{risk_level}",
            llm_callable=fake_llm,
        )

        assert review.output is not None
        assert review.output.risk_level.value == risk_level
        assert human_review is True
        assert audit["human_review_required"] is True
        assert audit["contradictor_risk_level"] == risk_level

    @pytest.mark.asyncio
    @pytest.mark.parametrize("risk_level", ["low", "medium"])
    async def test_low_medium_risk_does_not_trigger_human_review(
        self, orchestration_module, risk_level
    ):
        decision = _make_route_decision(requires_contradictor=True)

        async def fake_llm(prompt: str) -> str:
            return json.dumps(_valid_contradictor_payload(risk_level=risk_level))

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="board decision",
            agent_response="recommendation",
            correlation_id=f"cid-{risk_level}",
            llm_callable=fake_llm,
        )

        assert review.output is not None
        assert human_review is False
        assert audit["human_review_required"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Timeout is audited and never silent
# ═══════════════════════════════════════════════════════════════════════════════


class TestContradictorTimeoutAuditedNotSilent:
    @pytest.mark.asyncio
    async def test_contradictor_timeout_is_audited_and_does_not_silently_pass(
        self, orchestration_module, caplog
    ):
        """A timeout MUST produce status=timeout, human_review_required=True
        (since this is a required invocation that failed), and a structured
        audit log entry — never a silent success."""
        decision = _make_route_decision(requires_contradictor=True)

        async def slow_llm(prompt: str) -> str:
            await asyncio.sleep(10)  # longer than the test timeout
            return json.dumps(_valid_contradictor_payload())

        caplog.set_level(logging.WARNING)

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="board decision",
            agent_response="recommendation",
            correlation_id="cid-timeout",
            llm_callable=slow_llm,
            timeout_ms=100,  # 100ms forced timeout
        )

        from python.helpers.contradictor import schema as cs

        assert review.status == cs.ContradictorStatus.TIMEOUT
        assert review.output is None
        assert review.latency_ms is not None and review.latency_ms >= 0
        assert audit["contradictor_status"] == "timeout"
        assert audit["contradictor_invoked"] is True  # We tried — visible to audit
        assert human_review is True, (
            "Required-but-failed contradictor MUST escalate to human review"
        )
        # The orchestrator MUST log the timeout (no silent failure)
        timeout_logged = any(
            "timeout" in record.getMessage().lower() and "contradictor" in record.getMessage().lower()
            for record in caplog.records
        )
        assert timeout_logged, "Timeout must be logged for audit"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Invalid JSON output is rejected and audited
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvalidContradictorOutputRejectedAndAudited:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_payload",
        [
            "this is not json at all",
            "{not valid json: missing quotes}",
            json.dumps({"verdict": "challenge"}),  # missing required fields
            json.dumps({"verdict": "approve", "risk_level": "medium",
                       "contradictions": [], "missing_evidence": [],
                       "failure_modes": [], "legal_or_audit_risks": [],
                       "recommended_adjustments": [], "confidence": 0.5}),  # bad enum
        ],
    )
    async def test_invalid_contradictor_output_is_rejected_and_audited(
        self, orchestration_module, bad_payload, caplog
    ):
        """Invalid JSON or schema-noncompliant payload MUST yield
        status=schema_fail. NEVER must the orchestrator inject this content
        into the response envelope as if it were a successful review."""
        decision = _make_route_decision(requires_contradictor=True)

        async def bad_llm(prompt: str) -> str:
            return bad_payload

        caplog.set_level(logging.WARNING)

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="board decision",
            agent_response="recommendation",
            correlation_id="cid-bad-json",
            llm_callable=bad_llm,
        )

        from python.helpers.contradictor import schema as cs

        assert review.status == cs.ContradictorStatus.SCHEMA_FAIL
        assert review.output is None
        assert review.schema_errors, "schema errors must be captured"
        assert audit["contradictor_status"] == "schema_fail"
        assert audit["contradictor_invoked"] is True
        # Required + schema_fail => human review
        assert human_review is True
        schema_fail_logged = any(
            "schema_fail" in record.getMessage().lower() or "schema fail" in record.getMessage().lower()
            for record in caplog.records
        )
        assert schema_fail_logged, "schema_fail must be logged"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Audit trace contains all required structured fields
# ═══════════════════════════════════════════════════════════════════════════════


class TestContradictorAuditTrace:
    @pytest.mark.asyncio
    async def test_contradictor_audit_trace_contains_required_fields(
        self, orchestration_module
    ):
        """The audit dict MUST contain every required regulatory field."""
        decision = _make_route_decision(requires_contradictor=True)

        async def fake_llm(prompt: str) -> str:
            return json.dumps(_valid_contradictor_payload(risk_level="high"))

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="board decision",
            agent_response="recommendation",
            correlation_id="cid-audit",
            llm_callable=fake_llm,
        )

        required_fields = {
            "correlation_id",
            "requires_contradictor",
            "contradictor_invoked",
            "contradictor_status",
            "contradictor_latency_ms",
            "contradictor_verdict",
            "contradictor_risk_level",
            "contradictor_confidence",
            "contradictor_profile",
            "human_review_required",
            "input_hash",
            "output_hash",
            "response_hash",
            "route_decision_hash",
        }
        missing = required_fields - set(audit.keys())
        assert not missing, f"Missing audit fields: {missing}"
        # Hashes must be stable, non-empty strings
        assert isinstance(audit["input_hash"], str) and audit["input_hash"]
        assert isinstance(audit["output_hash"], str) and audit["output_hash"]
        assert isinstance(audit["route_decision_hash"], str) and audit["route_decision_hash"]
        # S1172/traçabilité : la réponse auditée DOIT être hachée (cf. docstring "responses are hashed").
        assert isinstance(audit["response_hash"], str) and audit["response_hash"]
        assert audit["response_hash"] == orchestration_module._stable_hash("recommendation")
        assert audit["correlation_id"] == "cid-audit"
        assert audit["requires_contradictor"] is True
        assert audit["contradictor_invoked"] is True
        assert audit["contradictor_status"] == "success"
        assert audit["contradictor_verdict"] == "challenge"
        assert audit["contradictor_risk_level"] == "high"
        # Audit must NOT leak raw user question (no PII)
        assert "board decision" not in json.dumps(audit), (
            "raw user question MUST NOT appear in audit (hash only)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: Application profile mapping does not fallback to default
# ═══════════════════════════════════════════════════════════════════════════════


class TestContradictorProfileMappingNoFallback:
    def test_contradictor_profile_mapping_does_not_fallback_to_default(self):
        """The application-side intent->profile mapping MUST map
        'contradictor' to 'contradictor', never to 'default'.

        The map under test is the one used by the delegation orchestrator
        (`call_subordinate.py`). The audit-only mapping in
        `router/metrics.py` is explicitly out of scope.
        """
        # Open the source of truth: the orchestrator file.
        import inspect
        from python.tools import call_subordinate as cs_mod

        source = inspect.getsource(cs_mod)
        # Extract the intent_to_profile literal embedded in the orchestrator.
        # We just assert the critical mapping is present and not silently mapped to default.
        assert '"contradictor": "contradictor"' in source, (
            "Application mapping intent_to_profile MUST contain "
            '"contradictor": "contradictor" — not fallback to default'
        )
        assert '"contradictor": "default"' not in source, (
            "Application mapping MUST NOT silently map contradictor to default"
        )

    def test_canonical_profile_mapping_module_no_fallback(self):
        """A canonical profile mapping helper MUST exist in the contradictor
        module and MUST explicitly map 'contradictor' to 'contradictor'."""
        from python.helpers.contradictor import profile_mapping as pm

        assert pm.INTENT_TO_PROFILE["contradictor"] == "contradictor"
        # Defensive: no key should be silently mapped to "default" if it has a
        # dedicated profile directory under agents/.
        assert pm.INTENT_TO_PROFILE.get("contradictor") != "default"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration sanity: deterministic invocation through the orchestrator
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrchestratorIntegrationSanity:
    @pytest.mark.asyncio
    async def test_orchestrator_does_not_invoke_when_flag_absent_via_router(
        self, orchestration_module
    ):
        """End-to-end: a non-board-level mono-intent request MUST NOT invoke
        the contradictor."""
        decision = decide_route("ecris le code python d'un compteur simple")
        assert decision.requires_contradictor is False

        called = 0

        async def spy(prompt: str) -> str:
            nonlocal called
            called += 1
            return "{}"

        review, human_review, audit = await orchestration_module.process_contradictor_for_response(
            route_decision=decision,
            user_question="code python compteur",
            agent_response="def compteur(): ...",
            correlation_id="cid-sanity",
            llm_callable=spy,
        )

        from python.helpers.contradictor import schema as cs

        assert called == 0
        assert review.status == cs.ContradictorStatus.SKIPPED
        assert human_review is False
        assert audit["contradictor_invoked"] is False

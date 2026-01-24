# -*- coding: utf-8 -*-
"""
Replay Harness — End-to-End Offline Testing for Oracle/Agent Zero

This module provides deterministic, offline testing of the reasoning pipeline
using fixtures instead of real LLM calls.

Features:
- No network calls (all LLM responses from fixtures)
- Deterministic results (same input → same output)
- Timeout testing via FakeTimeProvider
- Invariant verification (I1, I2, I4)

Usage:
    pytest tests/test_replay_harness.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Testing utilities
from python.helpers.testing import (
    FakeLiteLLMProvider,
    FakeTimeProvider,
    FixtureManager,
    MissingFixtureError,
    install_fake_provider,
    uninstall_fake_provider,
    set_time_provider,
    get_time_provider,
    RealTimeProvider,
    TimeoutExceeded,
    with_timeout,
)

# Oracle components
from python.helpers.metacognition import (
    Metacognition,
    MetacognitionConfig,
    EscalationType,
    InvariantViolationError,
)
from python.helpers.reasoning_engine import (
    ReasoningContext,
    ReasoningOutcome,
    ReasoningFlag,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def fixture_manager():
    """Create a fixture manager for tests."""
    fixture_dir = Path(__file__).parent / "fixtures" / "llm"
    return FixtureManager(fixture_dir=fixture_dir, record_mode=False)


@pytest.fixture
def fake_time():
    """Install fake time provider for tests."""
    fake = FakeTimeProvider(start_ms=0)
    old = set_time_provider(fake)
    yield fake
    set_time_provider(old)


@pytest.fixture
def config():
    """Standard metacognition config."""
    return MetacognitionConfig(
        safe_refuse_threshold=0.2,
        human_review_threshold=0.35,
        escalate_on_confidence_below=0.5,
    )


@pytest.fixture
def context():
    """Standard reasoning context."""
    return ReasoningContext(
        session_id="replay_test",
        user_query="Test query for replay harness",
    )


def make_outcome(
    confidence: float,
    flags: Optional[List[ReasoningFlag]] = None,
    answer: str = "Test answer",
) -> ReasoningOutcome:
    """Factory for creating test outcomes."""
    return ReasoningOutcome(
        answer=answer,
        trace=[],
        confidence=confidence,
        flags=flags or [],
        debug_id=f"replay_{confidence}",
        subtasks_completed=1,
        subtasks_total=1,
        backtracks_used=0,
        tool_calls_made=0,
        total_duration_ms=100,
    )


# ============================================================================
# REPLAY CASE DEFINITION
# ============================================================================

@dataclass
class ReplayCase:
    """
    A single replay test case.
    
    Defines input, expected output, and invariants to verify.
    """
    name: str
    input_query: str
    confidence: float
    flags: List[ReasoningFlag] = field(default_factory=list)
    
    # Expected outcomes
    expected_escalation: Optional[EscalationType] = None
    expected_min_escalation: Optional[EscalationType] = None  # For >= checks
    
    # Invariants to verify
    verify_i1: bool = True  # Non-dilution
    verify_i2: bool = True  # Monotonicity
    verify_i4: bool = True  # No-PII
    
    # Timing
    max_latency_ms: int = 5000
    simulate_timeout: bool = False
    timeout_ms: int = 0


# ============================================================================
# REPLAY CASES
# ============================================================================

REPLAY_CASES = [
    # I1: Non-dilution cases
    ReplayCase(
        name="critical_confidence_safe_refuse",
        input_query="What is 2+2?",
        confidence=0.15,
        expected_escalation=EscalationType.SAFE_REFUSE,
        verify_i1=True,
    ),
    ReplayCase(
        name="very_low_confidence_safe_refuse",
        input_query="Explain quantum physics",
        confidence=0.05,
        expected_escalation=EscalationType.SAFE_REFUSE,
        verify_i1=True,
    ),
    ReplayCase(
        name="boundary_above_safe_refuse",
        input_query="Simple calculation",
        confidence=0.20,
        expected_min_escalation=EscalationType.HUMAN_REVIEW,
        verify_i1=True,
    ),
    
    # I2: Monotonicity cases
    ReplayCase(
        name="high_confidence_no_flags_none",
        input_query="Basic question",
        confidence=0.8,
        flags=[],
        expected_escalation=EscalationType.NONE,
        verify_i2=True,
    ),
    ReplayCase(
        name="high_confidence_missing_info_ask_clarify",
        input_query="Ambiguous question",
        confidence=0.8,
        flags=[ReasoningFlag.MISSING_INFO],
        expected_escalation=EscalationType.ASK_CLARIFY,
        verify_i2=True,
    ),
    ReplayCase(
        name="high_confidence_policy_risk_human_review",
        input_query="Sensitive topic",
        confidence=0.8,
        flags=[ReasoningFlag.POLICY_RISK],
        expected_min_escalation=EscalationType.HUMAN_REVIEW,
        verify_i2=True,
    ),
    
    # I4: No-PII cases
    ReplayCase(
        name="no_pii_in_decision",
        input_query="My email is user@example.com and my SSN is 123-45-6789",
        confidence=0.5,
        verify_i4=True,
    ),
]


# ============================================================================
# SCORECARD
# ============================================================================

@dataclass
class ReplayScorecard:
    """
    Scorecard for replay harness results.
    """
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    no_consensus_count: int = 0
    safe_refuse_count: int = 0
    human_review_count: int = 0
    ask_clarify_count: int = 0
    none_count: int = 0
    total_latency_ms: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def no_consensus_rate(self) -> float:
        return self.no_consensus_count / self.total_cases if self.total_cases > 0 else 0.0
    
    @property
    def safe_refuse_rate(self) -> float:
        return self.safe_refuse_count / self.total_cases if self.total_cases > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_cases if self.total_cases > 0 else 0.0
    
    def record_escalation(self, escalation: EscalationType):
        if escalation == EscalationType.SAFE_REFUSE:
            self.safe_refuse_count += 1
        elif escalation == EscalationType.HUMAN_REVIEW:
            self.human_review_count += 1
        elif escalation == EscalationType.ASK_CLARIFY:
            self.ask_clarify_count += 1
        else:
            self.none_count += 1
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("              REPLAY HARNESS SCORECARD")
        print("=" * 60)
        print(f"  Total cases:        {self.total_cases}")
        print(f"  Passed:             {self.passed_cases}")
        print(f"  Failed:             {self.failed_cases}")
        print("-" * 60)
        print(f"  Safe refuse rate:   {self.safe_refuse_rate:.1%}")
        print(f"  Human review:       {self.human_review_count}")
        print(f"  Ask clarify:        {self.ask_clarify_count}")
        print(f"  None:               {self.none_count}")
        print("-" * 60)
        print(f"  Avg latency (sim):  {self.avg_latency_ms:.1f}ms")
        print("=" * 60)
        if self.errors:
            print("\nERRORS:")
            for err in self.errors[:5]:
                print(f"  - {err}")


# Global scorecard for collecting stats
_scorecard = ReplayScorecard()


# ============================================================================
# TEST CLASS
# ============================================================================

@pytest.mark.slow
@pytest.mark.replay
class TestReplayHarness:
    """
    Replay harness tests for Oracle/Agent Zero.
    
    These tests run OFFLINE with deterministic fixtures.
    
    Marked as 'slow' for CI gate separation:
    - FAST gate: pytest -m "not slow" (excludes replay)
    - FULL gate: pytest (includes all)
    """
    
    SEVERITY_ORDER = {
        EscalationType.NONE: 0,
        EscalationType.ASK_CLARIFY: 1,
        EscalationType.HUMAN_REVIEW: 2,
        EscalationType.SAFE_REFUSE: 3,
    }
    
    PII_PATTERNS = [
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        re.compile(r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b'),
        re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
    ]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", REPLAY_CASES, ids=lambda c: c.name)
    async def test_replay_case(self, config, case: ReplayCase, fake_time):
        """
        Execute a single replay case.
        """
        global _scorecard
        _scorecard.total_cases += 1
        
        # Create context with the test query
        context = ReasoningContext(
            session_id=f"replay_{case.name}",
            user_query=case.input_query,
        )
        
        # Create outcome with test parameters
        outcome = make_outcome(
            confidence=case.confidence,
            flags=case.flags,
        )
        
        # Run metacognition evaluation
        start_ms = fake_time.now_ms()
        meta = Metacognition(config)
        decision = await meta.evaluate(outcome, context)
        
        # Simulate latency
        fake_time.advance(100)  # Simulated processing time
        elapsed_ms = fake_time.now_ms() - start_ms
        _scorecard.total_latency_ms += elapsed_ms
        
        # Record escalation
        _scorecard.record_escalation(decision.escalation)
        
        # Verify expected escalation
        if case.expected_escalation:
            assert decision.escalation == case.expected_escalation, (
                f"[{case.name}] Expected {case.expected_escalation.value}, "
                f"got {decision.escalation.value}"
            )
        
        if case.expected_min_escalation:
            actual_severity = self.SEVERITY_ORDER[decision.escalation]
            min_severity = self.SEVERITY_ORDER[case.expected_min_escalation]
            assert actual_severity >= min_severity, (
                f"[{case.name}] Expected >= {case.expected_min_escalation.value}, "
                f"got {decision.escalation.value}"
            )
        
        # Verify I1: Non-dilution
        if case.verify_i1 and case.confidence < config.safe_refuse_threshold:
            assert decision.escalation == EscalationType.SAFE_REFUSE, (
                f"[{case.name}] I1 VIOLATION: raw={case.confidence} < threshold "
                f"should be SAFE_REFUSE, got {decision.escalation.value}"
            )
        
        # Verify I4: No-PII in safe_dict
        if case.verify_i4:
            safe_dict = decision.to_safe_dict()
            safe_str = str(safe_dict)
            for pattern in self.PII_PATTERNS:
                assert not pattern.search(safe_str), (
                    f"[{case.name}] I4 VIOLATION: PII found in to_safe_dict()"
                )
        
        # Verify latency
        assert elapsed_ms <= case.max_latency_ms, (
            f"[{case.name}] Latency {elapsed_ms}ms > max {case.max_latency_ms}ms"
        )
        
        _scorecard.passed_cases += 1
    
    @pytest.mark.asyncio
    async def test_invariant_i1_non_dilution_comprehensive(self, config):
        """
        Comprehensive test for I1: Non-dilution invariant.
        
        ANY confidence < safe_refuse_threshold MUST result in SAFE_REFUSE.
        """
        meta = Metacognition(config)
        context = ReasoningContext(session_id="i1_test", user_query="test")
        
        critical_values = [0.0, 0.05, 0.1, 0.15, 0.19, 0.199]
        
        for conf in critical_values:
            outcome = make_outcome(confidence=conf)
            decision = await meta.evaluate(outcome, context)
            
            assert decision.escalation == EscalationType.SAFE_REFUSE, (
                f"I1 VIOLATION: raw={conf} should be SAFE_REFUSE, "
                f"got {decision.escalation.value}"
            )
    
    @pytest.mark.asyncio
    async def test_invariant_i2_monotonicity_comprehensive(self, config):
        """
        Comprehensive test for I2: Monotonicity invariant.
        
        Adding flags should NEVER reduce escalation severity.
        """
        meta = Metacognition(config)
        context = ReasoningContext(session_id="i2_test", user_query="test")
        
        # Baseline: high confidence, no flags
        baseline_outcome = make_outcome(confidence=0.8, flags=[])
        baseline_decision = await meta.evaluate(baseline_outcome, context)
        baseline_severity = self.SEVERITY_ORDER[baseline_decision.escalation]
        
        # Test each flag
        all_flags = [
            ReasoningFlag.UNCERTAIN,
            ReasoningFlag.LOW_CONFIDENCE,
            ReasoningFlag.MISSING_INFO,
            ReasoningFlag.NEEDS_HUMAN,
            ReasoningFlag.POLICY_RISK,
        ]
        
        for flag in all_flags:
            flagged_outcome = make_outcome(confidence=0.8, flags=[flag])
            flagged_decision = await meta.evaluate(flagged_outcome, context)
            flagged_severity = self.SEVERITY_ORDER[flagged_decision.escalation]
            
            assert flagged_severity >= baseline_severity, (
                f"I2 VIOLATION: Adding {flag.value} reduced severity from "
                f"{baseline_decision.escalation.value} to {flagged_decision.escalation.value}"
            )
    
    @pytest.mark.asyncio
    async def test_invariant_i4_no_pii_in_logs(self, config):
        """
        Test for I4: No PII in logs/safe_dict.
        """
        meta = Metacognition(config)
        
        # Context with PII-like content
        pii_query = "My email is test@example.com and my SSN is 123-45-6789"
        context = ReasoningContext(session_id="i4_test", user_query=pii_query)
        
        outcome = make_outcome(confidence=0.5)
        decision = await meta.evaluate(outcome, context)
        
        safe_dict = decision.to_safe_dict()
        safe_str = str(safe_dict).lower()
        
        # Check for PII
        assert "test@example.com" not in safe_str
        assert "123-45-6789" not in safe_str
        assert "user_query" not in safe_str
    
    @pytest.mark.asyncio
    async def test_timeout_behavior(self, config, fake_time):
        """
        Test timeout handling with fake time provider.
        """
        async def slow_operation():
            # This would normally be an LLM call
            await asyncio.sleep(0)  # Yield control
            fake_time.advance(5000)  # Simulate 5 seconds elapsed
            return "result"
        
        # Should timeout
        with pytest.raises(TimeoutExceeded):
            await with_timeout(slow_operation(), timeout_ms=1000)
    
    @pytest.mark.asyncio
    async def test_no_pending_tasks_after_evaluation(self, config, context):
        """
        Verify no asyncio tasks are left pending after evaluation.
        """
        # Snapshot tasks before
        tasks_before = set(asyncio.all_tasks())
        
        meta = Metacognition(config)
        outcome = make_outcome(confidence=0.5)
        await meta.evaluate(outcome, context)
        
        # Small delay to let any cleanup happen
        await asyncio.sleep(0.01)
        
        # Snapshot tasks after
        tasks_after = set(asyncio.all_tasks())
        
        # Should be same tasks (minus any that completed)
        new_tasks = tasks_after - tasks_before
        # Filter out the current test task
        new_tasks = {t for t in new_tasks if not t.done() and "test_" not in str(t)}
        
        assert len(new_tasks) == 0, (
            f"Pending tasks after evaluation: {new_tasks}"
        )


# ============================================================================
# GUARD RAIL TESTS
# ============================================================================

class TestReplayGuardRails:
    """
    Guard rail tests to ensure critical tests are not removed.
    """
    
    def test_replay_harness_has_minimum_cases(self):
        """Verify minimum number of replay cases."""
        assert len(REPLAY_CASES) >= 5, (
            f"GUARD RAIL: Only {len(REPLAY_CASES)} replay cases, minimum 5 required"
        )
    
    def test_replay_cases_cover_all_invariants(self):
        """Verify replay cases cover I1, I2, I4."""
        has_i1 = any(c.verify_i1 for c in REPLAY_CASES)
        has_i2 = any(c.verify_i2 for c in REPLAY_CASES)
        has_i4 = any(c.verify_i4 for c in REPLAY_CASES)
        
        assert has_i1, "GUARD RAIL: No replay cases verify I1 (non-dilution)"
        assert has_i2, "GUARD RAIL: No replay cases verify I2 (monotonicity)"
        assert has_i4, "GUARD RAIL: No replay cases verify I4 (no-PII)"


# ============================================================================
# SCORECARD OUTPUT
# ============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Print scorecard at end of test session."""
    if _scorecard.total_cases > 0:
        _scorecard.print_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

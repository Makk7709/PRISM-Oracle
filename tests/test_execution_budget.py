"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              TESTS — Execution Budget / Anti-Infinite-Loop Guards           ║
║                                                                            ║
║  Validates that all loop guards trigger correctly and stop execution.      ║
║  Covers: iterations, depth, delegations, cycles, LLM calls, tool calls,   ║
║          deadlines, self-delegation, consensus rounds, budget propagation. ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import time
import pytest

from python.helpers.execution_budget import (
    BudgetExceededError,
    BudgetLimits,
    ExecutionState,
    StopReason,
    check_iteration,
    check_depth,
    check_delegation,
    check_tool_call,
    check_llm_call,
    check_consensus_round,
    get_default_limits,
    format_budget_exceeded_response,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def state():
    return ExecutionState(execution_id="test-001")


@pytest.fixture
def strict_limits():
    """Very strict limits for testing guard triggers."""
    return BudgetLimits(
        max_iterations=3,
        max_depth=2,
        max_delegations=2,
        max_tool_calls=4,
        max_llm_calls=5,
        max_consensus_rounds=2,
        deadline_seconds=60.0,
        allow_self_delegation=False,
        max_delegation_revisits=1,
    )


@pytest.fixture
def permissive_limits():
    """Permissive limits for testing normal execution."""
    return BudgetLimits(
        max_iterations=100,
        max_depth=20,
        max_delegations=50,
        max_tool_calls=200,
        max_llm_calls=100,
        max_consensus_rounds=10,
        deadline_seconds=600.0,
        allow_self_delegation=True,
        max_delegation_revisits=10,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: MAX ITERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMaxIterations:

    def test_iterations_within_budget(self, state, strict_limits):
        """Normal execution stays within iteration limit."""
        for _ in range(strict_limits.max_iterations):
            check_iteration(state, strict_limits, "TestAgent")
        assert state.current_iterations == strict_limits.max_iterations

    def test_iterations_exceed_budget(self, state, strict_limits):
        """Exceeding max_iterations triggers LOOP_GUARD."""
        for _ in range(strict_limits.max_iterations):
            check_iteration(state, strict_limits, "TestAgent")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_iteration(state, strict_limits, "TestAgent")

        assert exc_info.value.reason == StopReason.MAX_ITERATIONS_REACHED
        assert "TestAgent" in exc_info.value.detail

    def test_iteration_counter_increments(self, state, strict_limits):
        """Iteration counter increments correctly."""
        check_iteration(state, strict_limits, "A")
        assert state.current_iterations == 1
        check_iteration(state, strict_limits, "A")
        assert state.current_iterations == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: MAX DEPTH
# ═══════════════════════════════════════════════════════════════════════════════

class TestMaxDepth:

    def test_depth_within_budget(self, state, strict_limits):
        """Normal depth stays within limit."""
        for _ in range(strict_limits.max_depth):
            check_depth(state, strict_limits, "TestAgent")
        assert state.current_depth == strict_limits.max_depth

    def test_depth_exceed_budget(self, state, strict_limits):
        """Exceeding max_depth triggers LOOP_GUARD."""
        for _ in range(strict_limits.max_depth):
            check_depth(state, strict_limits, "TestAgent")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_depth(state, strict_limits, "TestAgent")

        assert exc_info.value.reason == StopReason.MAX_DEPTH_REACHED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: DELEGATION GUARDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDelegationGuards:

    def test_delegation_within_budget(self, state, strict_limits):
        """Normal delegations within limit."""
        check_delegation(state, strict_limits, "AgentA", "researcher")
        check_delegation(state, strict_limits, "AgentA", "legal_safe")
        assert state.current_delegations == 2

    def test_delegation_exceed_budget(self, state, strict_limits):
        """Exceeding max_delegations triggers LOOP_GUARD."""
        check_delegation(state, strict_limits, "A", "B")
        check_delegation(state, strict_limits, "B", "C")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_delegation(state, strict_limits, "C", "D")

        assert exc_info.value.reason == StopReason.MAX_DELEGATIONS_REACHED

    def test_self_delegation_blocked(self, state, strict_limits):
        """Agent delegating to itself is blocked."""
        with pytest.raises(BudgetExceededError) as exc_info:
            check_delegation(state, strict_limits, "legal_safe", "legal_safe")

        assert exc_info.value.reason == StopReason.SELF_DELEGATION_BLOCKED

    def test_self_delegation_allowed_when_configured(self, state):
        """Self-delegation allowed when explicitly configured."""
        limits = BudgetLimits(
            max_delegations=10,
            allow_self_delegation=True,
            max_delegation_revisits=5,
        )
        check_delegation(state, limits, "researcher", "researcher")
        assert state.current_delegations == 1

    def test_cycle_A_B_A_detected(self, state, strict_limits):
        """A→B→A cycle is detected and blocked."""
        check_delegation(state, strict_limits, "main", "AgentA")
        check_delegation(state, strict_limits, "AgentA", "AgentB")

        # AgentB trying to delegate back to AgentA (2nd visit)
        # max_delegation_revisits=1 means 1 revisit allowed (total 2 visits)
        # This is the 2nd visit to AgentA — still allowed

        # But we also hit max_delegations=2, so the 3rd delegation is blocked
        with pytest.raises(BudgetExceededError) as exc_info:
            check_delegation(state, strict_limits, "AgentB", "AgentA")

        assert exc_info.value.reason == StopReason.MAX_DELEGATIONS_REACHED

    def test_cycle_detection_with_higher_limits(self, state):
        """Cycle detection works independently of delegation count."""
        limits = BudgetLimits(
            max_delegations=100,
            max_delegation_revisits=0,  # NO revisits allowed
            allow_self_delegation=False,
        )
        check_delegation(state, limits, "main", "AgentA")
        check_delegation(state, limits, "AgentA", "AgentB")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_delegation(state, limits, "AgentB", "AgentA")

        assert exc_info.value.reason == StopReason.DELEGATION_CYCLE_DETECTED
        assert "AgentA" in exc_info.value.detail

    def test_delegation_chain_tracking(self, state, permissive_limits):
        """Delegation chain is correctly recorded."""
        check_delegation(state, permissive_limits, "main", "researcher")
        check_delegation(state, permissive_limits, "researcher", "legal_safe")
        check_delegation(state, permissive_limits, "legal_safe", "finance")

        assert state.delegation_chain == ["researcher", "legal_safe", "finance"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: TOOL CALL GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolCallGuard:

    def test_tool_calls_within_budget(self, state, strict_limits):
        """Normal tool calls within limit."""
        for i in range(strict_limits.max_tool_calls):
            check_tool_call(state, strict_limits, f"tool_{i}", "TestAgent")
        assert state.current_tool_calls == strict_limits.max_tool_calls

    def test_tool_calls_exceed_budget(self, state, strict_limits):
        """Exceeding max_tool_calls triggers LOOP_GUARD."""
        for i in range(strict_limits.max_tool_calls):
            check_tool_call(state, strict_limits, f"tool_{i}", "TestAgent")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_tool_call(state, strict_limits, "one_more", "TestAgent")

        assert exc_info.value.reason == StopReason.MAX_TOOL_CALLS_REACHED
        assert "one_more" in exc_info.value.detail


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: LLM CALL GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMCallGuard:

    def test_llm_calls_within_budget(self, state, strict_limits):
        """Normal LLM calls within limit."""
        for _ in range(strict_limits.max_llm_calls):
            check_llm_call(state, strict_limits, "TestAgent")
        assert state.current_llm_calls == strict_limits.max_llm_calls

    def test_llm_calls_exceed_budget(self, state, strict_limits):
        """Exceeding max_llm_calls triggers LOOP_GUARD."""
        for _ in range(strict_limits.max_llm_calls):
            check_llm_call(state, strict_limits, "TestAgent")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_llm_call(state, strict_limits, "TestAgent")

        assert exc_info.value.reason == StopReason.MAX_LLM_CALLS_REACHED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: CONSENSUS ROUND GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusRoundGuard:

    def test_consensus_within_budget(self, state, strict_limits):
        """Consensus rounds within limit."""
        for i in range(strict_limits.max_consensus_rounds):
            check_consensus_round(state, strict_limits, f"round_{i+1}")
        assert state.current_consensus_rounds == strict_limits.max_consensus_rounds

    def test_consensus_exceed_budget(self, state, strict_limits):
        """Exceeding consensus rounds triggers LOOP_GUARD."""
        for i in range(strict_limits.max_consensus_rounds):
            check_consensus_round(state, strict_limits, f"round_{i+1}")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_consensus_round(state, strict_limits, "extra_round")

        assert exc_info.value.reason == StopReason.MAX_CONSENSUS_ROUNDS_REACHED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: DEADLINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeadline:

    def test_deadline_exceeded(self):
        """Deadline triggers LOOP_GUARD."""
        state = ExecutionState(
            execution_id="test-deadline",
            started_at=time.time() - 100,  # started 100 seconds ago
        )
        limits = BudgetLimits(deadline_seconds=50.0, max_iterations=1000)

        with pytest.raises(BudgetExceededError) as exc_info:
            check_iteration(state, limits, "TestAgent")

        assert exc_info.value.reason == StopReason.DEADLINE_EXCEEDED

    def test_deadline_not_exceeded(self):
        """Execution within deadline is fine."""
        state = ExecutionState(
            execution_id="test-deadline-ok",
            started_at=time.time(),
        )
        limits = BudgetLimits(deadline_seconds=300.0, max_iterations=1000)
        check_iteration(state, limits, "TestAgent")
        assert state.current_iterations == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: SHARED BUDGET STATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestSharedBudgetState:

    def test_shared_state_across_agents(self, strict_limits):
        """Budget state is shared: subordinate increments count for superior."""
        state = ExecutionState(execution_id="test-shared")

        # Agent A uses 2 iterations
        check_iteration(state, strict_limits, "AgentA")
        check_iteration(state, strict_limits, "AgentA")
        assert state.current_iterations == 2

        # Agent B uses 1 more (same shared state) → 3 total = max
        check_iteration(state, strict_limits, "AgentB")
        assert state.current_iterations == 3

        # Next iteration by ANY agent triggers guard
        with pytest.raises(BudgetExceededError) as exc_info:
            check_iteration(state, strict_limits, "AgentC")

        assert exc_info.value.reason == StopReason.MAX_ITERATIONS_REACHED

    def test_mixed_budget_consumption(self, strict_limits):
        """Multiple budget dimensions consumed independently."""
        state = ExecutionState(execution_id="test-mixed")

        check_iteration(state, strict_limits, "A")
        check_tool_call(state, strict_limits, "search", "A")
        check_llm_call(state, strict_limits, "A")

        assert state.current_iterations == 1
        assert state.current_tool_calls == 1
        assert state.current_llm_calls == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: DEFAULT LIMITS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDefaultLimits:

    def test_defaults_are_conservative(self):
        """Default limits are present and conservative."""
        limits = get_default_limits()
        assert limits.max_iterations >= 5
        assert limits.max_iterations <= 50
        assert limits.max_depth >= 2
        assert limits.max_depth <= 10
        assert limits.max_delegations >= 3
        assert limits.max_delegations <= 20
        assert limits.max_tool_calls >= 10
        assert limits.max_tool_calls <= 100
        assert limits.max_llm_calls >= 10
        assert limits.max_llm_calls <= 50
        assert limits.max_consensus_rounds >= 2
        assert limits.max_consensus_rounds <= 5
        assert limits.deadline_seconds > 0
        assert limits.allow_self_delegation is False

    def test_env_override(self, monkeypatch):
        """Environment variables override defaults."""
        monkeypatch.setenv("EVIDENCE_MAX_ITERATIONS", "7")
        monkeypatch.setenv("EVIDENCE_MAX_DEPTH", "2")
        monkeypatch.setenv("EVIDENCE_MAX_DELEGATIONS", "3")

        limits = get_default_limits()
        assert limits.max_iterations == 7
        assert limits.max_depth == 2
        assert limits.max_delegations == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10: ERROR RESPONSE FORMAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorResponseFormat:

    def test_format_contains_reason(self, state, strict_limits):
        """Budget exceeded response contains structured info."""
        try:
            for _ in range(strict_limits.max_iterations + 1):
                check_iteration(state, strict_limits, "TestAgent")
        except BudgetExceededError as e:
            response = format_budget_exceeded_response(e)
            assert "MAX_ITERATIONS_REACHED" in response
            assert "Execution Budget Exceeded" in response
            assert "Iterations:" in response
            assert "Elapsed:" in response

    def test_state_to_dict(self, state):
        """ExecutionState serializes correctly."""
        state.current_iterations = 5
        state.current_depth = 2
        state.delegation_chain = ["A", "B"]

        d = state.to_dict()
        assert d["current_iterations"] == 5
        assert d["current_depth"] == 2
        assert d["delegation_chain"] == ["A", "B"]
        assert "elapsed_ms" in d
        assert isinstance(d["elapsed_ms"], (int, float))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11: NORMAL EXECUTION DOES NOT REGRESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalExecutionPath:

    def test_normal_workflow_within_budget(self, permissive_limits):
        """A typical workflow completes without hitting any guard."""
        state = ExecutionState(execution_id="test-normal")

        # Simulate: 10 iterations, 2 delegations, 8 tool calls, 10 LLM calls
        for _ in range(10):
            check_iteration(state, permissive_limits, "MainAgent")

        check_delegation(state, permissive_limits, "main", "researcher")
        check_delegation(state, permissive_limits, "researcher", "legal_safe")

        for i in range(8):
            check_tool_call(state, permissive_limits, f"tool_{i}", "MainAgent")

        for _ in range(10):
            check_llm_call(state, permissive_limits, "MainAgent")

        assert state.current_iterations == 10
        assert state.current_delegations == 2
        assert state.current_tool_calls == 8
        assert state.current_llm_calls == 10

    def test_single_delegation_round_trip(self, permissive_limits):
        """A single delegation + monologue + return stays within budget."""
        state = ExecutionState(execution_id="test-roundtrip")

        # Main agent iterates
        check_iteration(state, permissive_limits, "Main")
        check_llm_call(state, permissive_limits, "Main")

        # Delegation
        check_delegation(state, permissive_limits, "default", "researcher")
        check_depth(state, permissive_limits, "researcher")

        # Subordinate iterates
        for _ in range(3):
            check_iteration(state, permissive_limits, "researcher")
            check_llm_call(state, permissive_limits, "researcher")
            check_tool_call(state, permissive_limits, "search", "researcher")

        # Return to main
        check_iteration(state, permissive_limits, "Main")

        assert state.current_depth == 1
        assert state.current_delegations == 1
        assert state.current_iterations == 5  # 1 + 3 + 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12: ADVERSARIAL EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdversarialEdgeCases:

    def test_A_delegates_to_B_delegates_to_A_strict(self):
        """A→B→A cycle with strict no-revisit policy is blocked."""
        state = ExecutionState(execution_id="test-aba")
        limits = BudgetLimits(
            max_delegations=100,
            max_delegation_revisits=0,
            allow_self_delegation=False,
        )

        check_delegation(state, limits, "main", "A")
        check_delegation(state, limits, "A", "B")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_delegation(state, limits, "B", "A")

        assert exc_info.value.reason == StopReason.DELEGATION_CYCLE_DETECTED

    def test_monologue_without_exit(self):
        """Monologue that never hits break_loop still stops at max_iterations."""
        state = ExecutionState(execution_id="test-infinite-monologue")
        limits = BudgetLimits(max_iterations=5)

        for _ in range(5):
            check_iteration(state, limits, "Agent")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_iteration(state, limits, "Agent")

        assert exc_info.value.reason == StopReason.MAX_ITERATIONS_REACHED

    def test_tool_calling_agent_indefinitely(self):
        """Agent that calls tools indefinitely is stopped."""
        state = ExecutionState(execution_id="test-tool-spam")
        limits = BudgetLimits(max_tool_calls=3)

        check_tool_call(state, limits, "search", "Agent")
        check_tool_call(state, limits, "code_execution", "Agent")
        check_tool_call(state, limits, "search", "Agent")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_tool_call(state, limits, "search", "Agent")

        assert exc_info.value.reason == StopReason.MAX_TOOL_CALLS_REACHED

    def test_consensus_that_never_converges(self):
        """Consensus rounds that don't converge are stopped."""
        state = ExecutionState(execution_id="test-no-consensus")
        limits = BudgetLimits(max_consensus_rounds=2)

        check_consensus_round(state, limits, "round1")
        check_consensus_round(state, limits, "round2")

        with pytest.raises(BudgetExceededError) as exc_info:
            check_consensus_round(state, limits, "round3")

        assert exc_info.value.reason == StopReason.MAX_CONSENSUS_ROUNDS_REACHED

    def test_zero_budget_blocks_immediately(self):
        """Zero budget stops execution on first attempt."""
        state = ExecutionState(execution_id="test-zero")
        limits = BudgetLimits(max_iterations=0)

        with pytest.raises(BudgetExceededError) as exc_info:
            check_iteration(state, limits, "Agent")

        assert exc_info.value.reason == StopReason.MAX_ITERATIONS_REACHED

    def test_budget_not_reset_on_new_delegation(self):
        """Budget counters are NOT reset when creating a new subordinate."""
        state = ExecutionState(execution_id="test-no-reset")
        limits = BudgetLimits(max_iterations=5, max_delegations=100)

        # Use 3 iterations
        for _ in range(3):
            check_iteration(state, limits, "AgentA")

        # Delegation doesn't reset iterations
        check_delegation(state, limits, "default", "researcher")

        # Subordinate gets only 2 more iterations
        check_iteration(state, limits, "researcher")
        check_iteration(state, limits, "researcher")

        with pytest.raises(BudgetExceededError):
            check_iteration(state, limits, "researcher")

        assert state.current_iterations == 6

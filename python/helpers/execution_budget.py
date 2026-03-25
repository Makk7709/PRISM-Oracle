"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EXECUTION BUDGET — Anti-Infinite-Loop Guard              ║
║                                                                            ║
║  Centralized execution budget that prevents unbounded loops, delegation    ║
║  chains, LLM call explosions, and recursive agent invocations.            ║
║                                                                            ║
║  Every agent execution carries a budget. Every iteration, delegation,     ║
║  and LLM call decrements the budget. When a limit is reached, execution   ║
║  stops immediately with an explicit status.                                ║
║                                                                            ║
║  Principle: FAIL-CLOSED — in case of doubt, stop rather than continue.    ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("execution_budget")


# ═══════════════════════════════════════════════════════════════════════════════
# STOP REASONS
# ═══════════════════════════════════════════════════════════════════════════════

class StopReason(str, Enum):
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    MAX_DEPTH_REACHED = "MAX_DEPTH_REACHED"
    MAX_DELEGATIONS_REACHED = "MAX_DELEGATIONS_REACHED"
    MAX_TOOL_CALLS_REACHED = "MAX_TOOL_CALLS_REACHED"
    MAX_LLM_CALLS_REACHED = "MAX_LLM_CALLS_REACHED"
    MAX_CONSENSUS_ROUNDS_REACHED = "MAX_CONSENSUS_ROUNDS_REACHED"
    DELEGATION_CYCLE_DETECTED = "DELEGATION_CYCLE_DETECTED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    SELF_DELEGATION_BLOCKED = "SELF_DELEGATION_BLOCKED"


class BudgetExceededError(Exception):
    """Raised when any execution budget limit is reached."""

    def __init__(self, reason: StopReason, detail: str, state: "ExecutionState"):
        self.reason = reason
        self.detail = detail
        self.state = state
        super().__init__(f"EXECUTION_BUDGET_EXCEEDED: {reason.value} — {detail}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION (safe defaults, overridable via env)
# ═══════════════════════════════════════════════════════════════════════════════

def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key, "")
    if val.strip().isdigit():
        return int(val.strip())
    return default


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key, "")
    try:
        return float(val.strip()) if val.strip() else default
    except ValueError:
        return default


@dataclass(frozen=True)
class BudgetLimits:
    """
    Immutable execution limits. Safe defaults are conservative.
    Override via environment variables for production tuning.
    """
    max_iterations: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_ITERATIONS", 25))
    max_depth: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_DEPTH", 5))
    max_delegations: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_DELEGATIONS", 8))
    max_tool_calls: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_TOOL_CALLS", 50))
    max_llm_calls: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_LLM_CALLS", 30))
    max_consensus_rounds: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_CONSENSUS_ROUNDS", 3))
    deadline_seconds: float = field(default_factory=lambda: _env_float("EVIDENCE_DEADLINE_SECONDS", 900.0))
    allow_self_delegation: bool = False
    max_delegation_revisits: int = field(default_factory=lambda: _env_int("EVIDENCE_MAX_DELEGATION_REVISITS", 1))


def get_default_limits() -> BudgetLimits:
    """Returns BudgetLimits with safe defaults (reads env on each call)."""
    return BudgetLimits()


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION STATE (mutable, propagated through the execution chain)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionState:
    """
    Mutable execution counters. Propagated through the entire call chain.
    A single instance is shared by all agents in a delegation chain.
    """
    current_iterations: int = 0
    current_depth: int = 0
    current_delegations: int = 0
    current_tool_calls: int = 0
    current_llm_calls: int = 0
    current_consensus_rounds: int = 0
    started_at: float = field(default_factory=time.time)
    delegation_chain: List[str] = field(default_factory=list)
    delegation_visit_counts: Dict[str, int] = field(default_factory=dict)
    execution_id: str = ""

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "current_iterations": self.current_iterations,
            "current_depth": self.current_depth,
            "current_delegations": self.current_delegations,
            "current_tool_calls": self.current_tool_calls,
            "current_llm_calls": self.current_llm_calls,
            "current_consensus_rounds": self.current_consensus_rounds,
            "elapsed_ms": round(self.elapsed_ms),
            "delegation_chain": list(self.delegation_chain),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GUARD CHECKS (call before each operation)
# ═══════════════════════════════════════════════════════════════════════════════

def check_iteration(state: ExecutionState, limits: BudgetLimits, agent_name: str = "") -> None:
    """Call before each message loop iteration. Increments counter and checks limit."""
    state.current_iterations += 1

    if state.current_iterations > limits.max_iterations:
        _log_and_raise(
            StopReason.MAX_ITERATIONS_REACHED,
            f"Agent '{agent_name}' reached {state.current_iterations}/{limits.max_iterations} iterations",
            state, agent_name, limits,
        )

    _check_deadline(state, limits, agent_name)


def check_depth(state: ExecutionState, limits: BudgetLimits, agent_name: str = "") -> None:
    """Call before entering a deeper level (delegation, _process_chain). Increments depth."""
    state.current_depth += 1

    if state.current_depth > limits.max_depth:
        _log_and_raise(
            StopReason.MAX_DEPTH_REACHED,
            f"Agent '{agent_name}' reached depth {state.current_depth}/{limits.max_depth}",
            state, agent_name, limits,
        )


def check_delegation(
    state: ExecutionState,
    limits: BudgetLimits,
    source_agent: str,
    target_profile: str,
) -> None:
    """Call before delegating to a subordinate. Checks delegation count, cycles, self-delegation."""
    state.current_delegations += 1

    # Self-delegation guard
    if source_agent == target_profile and not limits.allow_self_delegation:
        _log_and_raise(
            StopReason.SELF_DELEGATION_BLOCKED,
            f"Agent '{source_agent}' attempted self-delegation to profile '{target_profile}'",
            state, source_agent, limits,
        )

    # Max delegations guard
    if state.current_delegations > limits.max_delegations:
        _log_and_raise(
            StopReason.MAX_DELEGATIONS_REACHED,
            f"Delegation count {state.current_delegations}/{limits.max_delegations} "
            f"(chain: {' → '.join(state.delegation_chain)})",
            state, source_agent, limits,
        )

    # Cycle detection: track visits per profile
    visit_count = state.delegation_visit_counts.get(target_profile, 0) + 1
    state.delegation_visit_counts[target_profile] = visit_count

    if visit_count > limits.max_delegation_revisits + 1:
        _log_and_raise(
            StopReason.DELEGATION_CYCLE_DETECTED,
            f"Profile '{target_profile}' visited {visit_count} times "
            f"(max revisits: {limits.max_delegation_revisits}). "
            f"Chain: {' → '.join(state.delegation_chain)} → {target_profile}",
            state, source_agent, limits,
        )

    state.delegation_chain.append(target_profile)


def check_tool_call(state: ExecutionState, limits: BudgetLimits, tool_name: str = "", agent_name: str = "") -> None:
    """Call before each tool execution."""
    state.current_tool_calls += 1

    if state.current_tool_calls > limits.max_tool_calls:
        _log_and_raise(
            StopReason.MAX_TOOL_CALLS_REACHED,
            f"Agent '{agent_name}' reached {state.current_tool_calls}/{limits.max_tool_calls} "
            f"tool calls (last tool: '{tool_name}')",
            state, agent_name, limits,
        )


def check_llm_call(state: ExecutionState, limits: BudgetLimits, agent_name: str = "") -> None:
    """Call before each LLM API call."""
    state.current_llm_calls += 1

    if state.current_llm_calls > limits.max_llm_calls:
        _log_and_raise(
            StopReason.MAX_LLM_CALLS_REACHED,
            f"Agent '{agent_name}' reached {state.current_llm_calls}/{limits.max_llm_calls} LLM calls",
            state, agent_name, limits,
        )

    _check_deadline(state, limits, agent_name)


def check_consensus_round(state: ExecutionState, limits: BudgetLimits, round_label: str = "") -> None:
    """Call before each consensus round."""
    state.current_consensus_rounds += 1

    if state.current_consensus_rounds > limits.max_consensus_rounds:
        _log_and_raise(
            StopReason.MAX_CONSENSUS_ROUNDS_REACHED,
            f"Consensus round {state.current_consensus_rounds}/{limits.max_consensus_rounds} "
            f"(label: '{round_label}')",
            state, "", limits,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_deadline(state: ExecutionState, limits: BudgetLimits, agent_name: str) -> None:
    if limits.deadline_seconds > 0 and state.elapsed_seconds > limits.deadline_seconds:
        _log_and_raise(
            StopReason.DEADLINE_EXCEEDED,
            f"Execution exceeded deadline: {state.elapsed_seconds:.1f}s / {limits.deadline_seconds}s",
            state, agent_name, limits,
        )


def _log_and_raise(
    reason: StopReason,
    detail: str,
    state: ExecutionState,
    agent_name: str,
    limits: BudgetLimits,
) -> None:
    """Log structured guard event and raise BudgetExceededError."""
    log_data = {
        "event": "LOOP_GUARD_TRIGGERED",
        "reason": reason.value,
        "detail": detail,
        "agent": agent_name,
        "execution_id": state.execution_id,
        **state.to_dict(),
        "limits": {
            "max_iterations": limits.max_iterations,
            "max_depth": limits.max_depth,
            "max_delegations": limits.max_delegations,
            "max_tool_calls": limits.max_tool_calls,
            "max_llm_calls": limits.max_llm_calls,
            "max_consensus_rounds": limits.max_consensus_rounds,
            "deadline_seconds": limits.deadline_seconds,
        },
    }
    logger.warning("LOOP_GUARD_TRIGGERED | %s | %s", reason.value, detail, extra=log_data)
    raise BudgetExceededError(reason, detail, state)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT INTEGRATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_BUDGET_STATE_KEY = "_execution_budget_state"
_BUDGET_LIMITS_KEY = "_execution_budget_limits"


def get_or_create_state(agent: Any) -> ExecutionState:
    """
    Get the ExecutionState from an agent, or create one.
    States are propagated from superior to subordinate agents.
    """
    state = agent.get_data(_BUDGET_STATE_KEY)
    if state is None:
        state = _new_state()
        agent.set_data(_BUDGET_STATE_KEY, state)
    return state


def reset_state(agent: Any) -> ExecutionState:
    """
    Force-create a fresh ExecutionState for a new execution cycle (e.g. new user message).
    Must be called at the start of monologue() to avoid stale started_at timestamps.
    """
    state = _new_state()
    agent.set_data(_BUDGET_STATE_KEY, state)
    return state


def _new_state() -> ExecutionState:
    import uuid
    return ExecutionState(execution_id=str(uuid.uuid4())[:12])


def get_limits(agent: Any) -> BudgetLimits:
    """Get the BudgetLimits from an agent, or return defaults."""
    limits = agent.get_data(_BUDGET_LIMITS_KEY)
    if limits is None:
        limits = get_default_limits()
        agent.set_data(_BUDGET_LIMITS_KEY, limits)
    return limits


def propagate_budget(source_agent: Any, target_agent: Any) -> None:
    """
    Propagate the SAME execution state and limits from a superior to a subordinate.
    This ensures the budget is shared across the entire delegation chain.
    """
    state = get_or_create_state(source_agent)
    limits = get_limits(source_agent)
    target_agent.set_data(_BUDGET_STATE_KEY, state)
    target_agent.set_data(_BUDGET_LIMITS_KEY, limits)


def format_budget_exceeded_response(error: BudgetExceededError) -> str:
    """Format a user-facing response when budget is exceeded."""
    return (
        f"## Execution Budget Exceeded\n\n"
        f"**Reason**: {error.reason.value}\n"
        f"**Detail**: {error.detail}\n\n"
        f"### Execution State\n"
        f"- Iterations: {error.state.current_iterations}\n"
        f"- Depth: {error.state.current_depth}\n"
        f"- Delegations: {error.state.current_delegations}\n"
        f"- Tool calls: {error.state.current_tool_calls}\n"
        f"- LLM calls: {error.state.current_llm_calls}\n"
        f"- Elapsed: {error.state.elapsed_ms:.0f}ms\n"
        f"- Delegation chain: {' → '.join(error.state.delegation_chain) or 'none'}\n\n"
        f"*The system stopped this execution to prevent runaway costs and unbounded processing. "
        f"You may retry with a simpler query or contact an administrator to adjust limits.*"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "StopReason",
    "BudgetExceededError",
    "BudgetLimits",
    "ExecutionState",
    "get_default_limits",
    "check_iteration",
    "check_depth",
    "check_delegation",
    "check_tool_call",
    "check_llm_call",
    "check_consensus_round",
    "get_or_create_state",
    "reset_state",
    "get_limits",
    "propagate_budget",
    "format_budget_exceeded_response",
]

"""
Tests unitaires SESSION 3 — PipelineTracker

Couverture :
- AgentStep : creation, role auto, duration_seconds, to_dict
- PipelineTracker : start/complete/skip, get_activated/non_activated, ordering
- Fail-safe : double start, complete sans start, complete deja complete
- Concurrence : start/complete entrelaces (threading)
- Performance : overhead < 1ms pour start+complete
- Registre : exhaustivite vs agents/ filesystem
- Rendu rapport : to_report_table, to_dict
- reset()
"""

import os
import time
import threading
from unittest.mock import patch

import pytest

from python.helpers.pipeline_tracker import (
    AgentStep,
    StepStatus,
    PipelineTracker,
    AGENT_ROLE_DESCRIPTIONS,
    _SYSTEM_AGENT_REGISTRY,
    _discover_agents_from_filesystem,
    get_full_agent_registry,
)


# AgentStep
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentStep:
    def test_default_status_is_pending(self):
        step = AgentStep(agent_name="researcher")
        assert step.status == StepStatus.PENDING

    def test_role_auto_resolved_from_registry(self):
        step = AgentStep(agent_name="finance")
        assert step.role_description == AGENT_ROLE_DESCRIPTIONS["finance"]
        assert "financier" in step.role_description

    def test_role_explicit_overrides_auto(self):
        step = AgentStep(agent_name="finance", role_description="Custom role")
        assert step.role_description == "Custom role"

    def test_unknown_agent_gets_default_role(self):
        step = AgentStep(agent_name="unknown_agent_xyz")
        assert step.role_description == "Agent specialise"

    def test_duration_seconds_none_when_no_duration(self):
        step = AgentStep(agent_name="researcher")
        assert step.duration_seconds is None

    def test_duration_seconds_computed(self):
        step = AgentStep(agent_name="researcher", duration_ms=1500)
        assert step.duration_seconds == 1.5

    def test_duration_seconds_zero(self):
        step = AgentStep(agent_name="researcher", duration_ms=0)
        assert step.duration_seconds == 0.0

    def test_to_dict_contains_all_fields(self):
        step = AgentStep(
            agent_name="legal_safe",
            status=StepStatus.COMPLETED,
            duration_ms=3200,
            started_at="2026-03-11T10:00:00+00:00",
            completed_at="2026-03-11T10:00:03+00:00",
        )
        d = step.to_dict()
        assert d["agent_name"] == "legal_safe"
        assert d["status"] == "completed"
        assert d["duration_ms"] == 3200
        assert "_start_monotonic" not in d

    def test_to_dict_excludes_private_fields(self):
        step = AgentStep(agent_name="researcher", _start_monotonic=12345.678)
        d = step.to_dict()
        assert "_start_monotonic" not in d


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineTracker — Core
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineTrackerCore:
    def test_empty_tracker_no_activated(self):
        tracker = PipelineTracker()
        assert tracker.get_activated() == []

    def test_empty_tracker_all_non_activated(self):
        tracker = PipelineTracker()
        non = tracker.get_non_activated()
        assert len(non) == len(tracker.registry)

    def test_start_and_complete_step(self):
        tracker = PipelineTracker()
        tracker.start_step("researcher")
        step = tracker.get_step("researcher")
        assert step is not None
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None

        tracker.complete_step("researcher")
        step = tracker.get_step("researcher")
        assert step.status == StepStatus.COMPLETED
        assert step.completed_at is not None
        assert step.duration_ms is not None
        assert step.duration_ms >= 0

    def test_complete_with_failure(self):
        tracker = PipelineTracker()
        tracker.start_step("finance")
        tracker.complete_step("finance", success=False, error="timeout")
        step = tracker.get_step("finance")
        assert step.status == StepStatus.FAILED
        assert step.error == "timeout"

    def test_skip_step(self):
        tracker = PipelineTracker()
        tracker.skip_step("hacker", reason="not needed")
        step = tracker.get_step("hacker")
        assert step.status == StepStatus.SKIPPED
        assert "hacker" not in [s.agent_name for s in tracker.get_activated()]

    def test_get_activated_order_preserved(self):
        tracker = PipelineTracker()
        for name in ["researcher", "finance", "marketing"]:
            tracker.start_step(name)
            tracker.complete_step(name)
        activated = tracker.get_activated()
        assert [s.agent_name for s in activated] == ["researcher", "finance", "marketing"]

    def test_get_non_activated_sorted(self):
        reg = frozenset({"alpha", "beta", "gamma"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("beta")
        tracker.complete_step("beta")
        non = tracker.get_non_activated()
        assert non == ["alpha", "gamma"]

    def test_get_non_activated_excludes_running(self):
        reg = frozenset({"a", "b"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("a")
        non = tracker.get_non_activated()
        assert non == ["b"]

    def test_get_non_activated_excludes_failed(self):
        reg = frozenset({"a", "b"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("a")
        tracker.complete_step("a", success=False, error="crash")
        non = tracker.get_non_activated()
        assert non == ["b"]

    def test_total_duration_ms(self):
        tracker = PipelineTracker()
        tracker.start_step("researcher")
        time.sleep(0.01)
        tracker.complete_step("researcher")
        tracker.start_step("finance")
        time.sleep(0.01)
        tracker.complete_step("finance")
        total = tracker.total_duration_ms()
        assert total >= 20

    def test_summary_counts(self):
        reg = frozenset({"a", "b", "c"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("a")
        tracker.complete_step("a")
        tracker.start_step("b")
        tracker.complete_step("b", success=False, error="err")
        tracker.skip_step("c")
        s = tracker.summary()
        assert s["completed"] == 1
        assert s["failed"] == 1
        assert s["skipped"] == 1

    def test_get_step_returns_none_for_unknown(self):
        tracker = PipelineTracker()
        assert tracker.get_step("nonexistent") is None

    def test_reset_clears_everything(self):
        tracker = PipelineTracker()
        tracker.start_step("researcher")
        tracker.complete_step("researcher")
        tracker.reset()
        assert tracker.get_activated() == []
        assert tracker.get_step("researcher") is None


# Fail-safe
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineTrackerFailSafe:
    def test_complete_without_start_creates_failed_step(self):
        tracker = PipelineTracker()
        tracker.complete_step("ghost_agent")
        step = tracker.get_step("ghost_agent")
        assert step is not None
        assert step.status == StepStatus.FAILED
        assert "without start_step" in step.error

    def test_double_start_overwrites_with_warning(self):
        tracker = PipelineTracker()
        tracker.start_step("researcher")
        first_start = tracker.get_step("researcher").started_at
        time.sleep(0.005)
        tracker.start_step("researcher")
        second_start = tracker.get_step("researcher").started_at
        assert second_start != first_start
        assert tracker.get_step("researcher").status == StepStatus.RUNNING

    def test_double_complete_is_noop(self):
        tracker = PipelineTracker()
        tracker.start_step("finance")
        tracker.complete_step("finance")
        first_completed = tracker.get_step("finance").completed_at
        tracker.complete_step("finance", success=False, error="retry")
        assert tracker.get_step("finance").completed_at == first_completed
        assert tracker.get_step("finance").status == StepStatus.COMPLETED

    def test_complete_failed_then_complete_again_is_noop(self):
        tracker = PipelineTracker()
        tracker.start_step("medical")
        tracker.complete_step("medical", success=False, error="crash")
        tracker.complete_step("medical", success=True)
        assert tracker.get_step("medical").status == StepStatus.FAILED


# Concurrence
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineTrackerConcurrency:
    def test_concurrent_start_complete_no_crash(self):
        """Simule des agents lances en parallele (start+complete entrelaces)."""
        tracker = PipelineTracker()
        agents = [f"agent_{i}" for i in range(20)]
        errors = []

        def run_agent(name):
            try:
                tracker.start_step(name)
                time.sleep(0.001)
                tracker.complete_step(name)
            except Exception as e:
                errors.append((name, e))

        threads = [threading.Thread(target=run_agent, args=(a,)) for a in agents]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Thread errors: {errors}"
        activated = tracker.get_activated()
        assert len(activated) == 20
        for step in activated:
            assert step.status == StepStatus.COMPLETED
            assert step.duration_ms is not None

    def test_interleaved_start_complete(self):
        """S1(A), S1(B), C1(A), C1(B) — entrelaces, pas de race."""
        tracker = PipelineTracker()
        tracker.start_step("a")
        tracker.start_step("b")
        tracker.complete_step("a")
        tracker.complete_step("b")
        assert tracker.get_step("a").status == StepStatus.COMPLETED
        assert tracker.get_step("b").status == StepStatus.COMPLETED
        assert tracker.get_step("a").duration_ms is not None
        assert tracker.get_step("b").duration_ms is not None


# Performance
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineTrackerPerformance:
    def test_start_complete_overhead_under_1ms(self):
        """start_step + complete_step < 1ms de latence cumulee."""
        tracker = PipelineTracker()
        iterations = 100
        total_ns = 0
        for i in range(iterations):
            name = f"perf_agent_{i}"
            t0 = time.perf_counter_ns()
            tracker.start_step(name)
            tracker.complete_step(name)
            total_ns += time.perf_counter_ns() - t0
        avg_us = (total_ns / iterations) / 1000
        assert avg_us < 1000, f"Average overhead {avg_us:.1f}us exceeds 1ms"


# ═══════════════════════════════════════════════════════════════════════════════
# Registre d'agents
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentRegistry:
    def test_static_registry_has_11_agents(self):
        assert len(_SYSTEM_AGENT_REGISTRY) == 11

    def test_static_registry_contains_all_known_agents(self):
        expected = {
            "default", "developer", "finance", "hacker",
            "legal_drafting_guarded", "legal_safe", "marketing",
            "medical", "multitask", "researcher", "sales",
        }
        assert _SYSTEM_AGENT_REGISTRY == expected

    def test_role_descriptions_cover_registry(self):
        for agent in _SYSTEM_AGENT_REGISTRY:
            assert agent in AGENT_ROLE_DESCRIPTIONS, f"Missing description for {agent}"

    def test_filesystem_discovery_returns_frozenset(self):
        result = _discover_agents_from_filesystem()
        assert isinstance(result, frozenset)
        assert len(result) >= 10

    def test_filesystem_excludes_underscore_dirs(self):
        result = _discover_agents_from_filesystem()
        for name in result:
            assert not name.startswith("_"), f"Underscore dir included: {name}"

    def test_full_registry_is_superset_of_static(self):
        full = get_full_agent_registry()
        assert full >= _SYSTEM_AGENT_REGISTRY

    def test_filesystem_fallback_on_missing_dir(self):
        with patch("python.helpers.pipeline_tracker.os.path.normpath", return_value="/nonexistent"):
            result = _discover_agents_from_filesystem()
            assert result == _SYSTEM_AGENT_REGISTRY


# Rendering
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineTrackerRendering:
    def test_to_report_table_with_activated(self):
        tracker = PipelineTracker(registry=frozenset({"a", "b", "c"}))
        tracker.start_step("a")
        tracker.complete_step("a")
        table = tracker.to_report_table()
        assert "Agents actives" in table
        assert "`a`" in table
        assert "Agents non actives" in table
        assert "`b`" in table
        assert "`c`" in table

    def test_to_report_table_empty(self):
        tracker = PipelineTracker(registry=frozenset({"x"}))
        table = tracker.to_report_table()
        assert "aucun agent active" in table

    def test_to_report_table_all_activated(self):
        reg = frozenset({"only"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("only")
        tracker.complete_step("only")
        table = tracker.to_report_table()
        assert "tous les agents" in table

    def test_to_dict_structure(self):
        reg = frozenset({"a", "b"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("a")
        tracker.complete_step("a")
        d = tracker.to_dict()
        assert "activated" in d
        assert "non_activated" in d
        assert "summary" in d
        assert "total_duration_ms" in d
        assert len(d["activated"]) == 1
        assert d["non_activated"] == ["b"]

    def test_to_dict_activated_step_serializable(self):
        """Verifie que to_dict produit des structures JSON-safe."""
        import json
        tracker = PipelineTracker(registry=frozenset({"x"}))
        tracker.start_step("x")
        tracker.complete_step("x")
        d = tracker.to_dict()
        serialized = json.dumps(d)
        assert '"agent_name": "x"' in serialized


# ═══════════════════════════════════════════════════════════════════════════════
# Duration accuracy (wall-clock via monotonic)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDurationAccuracy:
    def test_duration_reflects_real_elapsed_time(self):
        """Le duration_ms doit refleter le temps reel (wall-clock)."""
        tracker = PipelineTracker()
        tracker.start_step("slow_agent")
        time.sleep(0.05)
        tracker.complete_step("slow_agent")
        step = tracker.get_step("slow_agent")
        assert step.duration_ms >= 45, f"Expected >= 45ms, got {step.duration_ms}ms"
        assert step.duration_ms < 200, f"Expected < 200ms, got {step.duration_ms}ms"

    def test_duration_ms_is_zero_for_instant_step(self):
        tracker = PipelineTracker()
        tracker.start_step("fast_agent")
        tracker.complete_step("fast_agent")
        step = tracker.get_step("fast_agent")
        assert step.duration_ms is not None
        assert step.duration_ms >= 0
        assert step.duration_ms < 50

    def test_duration_none_for_synthetic_failed_step(self):
        """complete_step sans start_step = pas de duration fiable."""
        tracker = PipelineTracker()
        tracker.complete_step("orphan")
        step = tracker.get_step("orphan")
        assert step.duration_ms is None


# ═══════════════════════════════════════════════════════════════════════════════
# Custom registry
# ═══════════════════════════════════════════════════════════════════════════════

class TestCustomRegistry:
    def test_custom_registry_respected(self):
        reg = frozenset({"alpha", "beta"})
        tracker = PipelineTracker(registry=reg)
        assert tracker.registry == reg
        assert tracker.get_non_activated() == ["alpha", "beta"]

    def test_out_of_registry_agent_tracked_but_not_in_non_activated(self):
        """Un agent hors registre peut etre tracke mais n'apparait pas dans non_activated."""
        reg = frozenset({"a"})
        tracker = PipelineTracker(registry=reg)
        tracker.start_step("unknown_agent")
        tracker.complete_step("unknown_agent")
        assert len(tracker.get_activated()) == 1
        assert tracker.get_non_activated() == ["a"]

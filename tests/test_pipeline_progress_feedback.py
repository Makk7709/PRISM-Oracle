"""
Tests — Pipeline progress feedback (tasks 9.11-9.13).

Validates that emit_pipeline_progress / emit_delegation_progress
correctly call context.log.set_progress() with meaningful messages,
and that failures are silently swallowed (fail-safe).
"""

from unittest.mock import MagicMock

import pytest

from python.helpers.progress_feedback import (
    emit_delegation_progress,
    emit_pipeline_progress,
    emit_synthesis_progress,
)


def _make_mock_agent():
    """Create a minimal mock agent with context.log.set_progress."""
    agent = MagicMock()
    agent.context.log.set_progress = MagicMock()
    return agent


# ─── emit_pipeline_progress (strategic orchestrator path) ───────────────────


class TestEmitPipelineProgress:

    def test_message_contains_profile_and_step(self):
        agent = _make_mock_agent()
        emit_pipeline_progress(agent, "researcher", 2, 4)
        agent.context.log.set_progress.assert_called_once()
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "researcher" in msg
        assert "2/4" in msg

    def test_message_contains_role_description(self):
        agent = _make_mock_agent()
        emit_pipeline_progress(agent, "legal_safe", 1, 3)
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "conformite" in msg.lower() or "reglementation" in msg.lower()

    def test_unknown_profile_falls_back_to_profile_name(self):
        agent = _make_mock_agent()
        emit_pipeline_progress(agent, "custom_agent_xyz", 1, 1)
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "custom_agent_xyz" in msg

    def test_fail_safe_on_exception(self):
        agent = _make_mock_agent()
        agent.context.log.set_progress.side_effect = RuntimeError("boom")
        emit_pipeline_progress(agent, "researcher", 1, 2)

    def test_first_and_last_step(self):
        agent = _make_mock_agent()
        emit_pipeline_progress(agent, "finance", 1, 5)
        msg1 = agent.context.log.set_progress.call_args[0][0]
        assert "1/5" in msg1

        emit_pipeline_progress(agent, "sales", 5, 5)
        msg2 = agent.context.log.set_progress.call_args[0][0]
        assert "5/5" in msg2


# ─── emit_synthesis_progress ────────────────────────────────────────────────


class TestEmitSynthesisProgress:

    def test_message_contains_agent_count(self):
        agent = _make_mock_agent()
        emit_synthesis_progress(agent, 4)
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "4" in msg
        assert "synthese" in msg.lower() or "consolidation" in msg.lower()

    def test_fail_safe_on_exception(self):
        agent = _make_mock_agent()
        agent.context.log.set_progress.side_effect = RuntimeError("boom")
        emit_synthesis_progress(agent, 3)


# ─── emit_delegation_progress (call_subordinate path) ───────────────────────


class TestEmitDelegationProgress:

    def test_message_contains_profile_and_step(self):
        agent = _make_mock_agent()
        emit_delegation_progress(agent, "medical", 3)
        agent.context.log.set_progress.assert_called_once()
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "medical" in msg
        assert "3" in msg

    def test_message_contains_role_description(self):
        agent = _make_mock_agent()
        emit_delegation_progress(agent, "developer", 1)
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "code" in msg.lower() or "architecture" in msg.lower() or "developer" in msg.lower()

    def test_unknown_profile_falls_back_to_profile_name(self):
        agent = _make_mock_agent()
        emit_delegation_progress(agent, "my_custom_agent", 2)
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "my_custom_agent" in msg

    def test_fail_safe_on_exception(self):
        agent = _make_mock_agent()
        agent.context.log.set_progress.side_effect = RuntimeError("crash")
        emit_delegation_progress(agent, "researcher", 1)

    def test_default_profile(self):
        agent = _make_mock_agent()
        emit_delegation_progress(agent, "default", 1)
        msg = agent.context.log.set_progress.call_args[0][0]
        assert "default" in msg
        assert "generaliste" in msg.lower()

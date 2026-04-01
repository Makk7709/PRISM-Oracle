"""
Progress feedback helpers for multi-agent pipelines.

These functions update the UI progress bar (via context.log.set_progress)
to inform the user which agent is currently executing during long pipelines.

All functions are fail-safe: exceptions are silently swallowed so the
pipeline execution is never impacted by a progress display failure.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from python.helpers.pipeline_tracker import AGENT_ROLE_DESCRIPTIONS

if TYPE_CHECKING:
    from agent import Agent

logger = logging.getLogger("progress_feedback")


def emit_pipeline_progress(
    agent: "Agent", profile: str, step: int, total: int,
) -> None:
    """Update the UI progress bar with current agent step in a pipeline."""
    try:
        role = AGENT_ROLE_DESCRIPTIONS.get(profile, profile)
        agent.context.log.set_progress(
            f"Agent {profile} en cours ({step}/{total}) \u2014 {role}"
        )
    except Exception:
        pass


def emit_synthesis_progress(agent: "Agent", total_agents: int) -> None:
    """Update the UI progress bar during the consolidation phase."""
    try:
        agent.context.log.set_progress(
            f"Synthese en cours \u2014 consolidation de {total_agents} analyses"
        )
    except Exception:
        pass


def emit_delegation_progress(agent: "Agent", profile: str, step_no: int) -> None:
    """Update the UI progress bar when a subordinate agent starts."""
    try:
        role = AGENT_ROLE_DESCRIPTIONS.get(profile, profile)
        agent.context.log.set_progress(
            f"Agent {profile} en cours (etape {step_no}) \u2014 {role}"
        )
    except Exception:
        pass

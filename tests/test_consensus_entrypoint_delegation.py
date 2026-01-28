"""
Entrypoint delegation tests for PRISM consensus.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import time
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.consensus.engine import ConsensusDecision
from python.helpers.consensus_manager import VoteCount
from python.helpers.consensus_contracts import ConsensusStatusEnum, ConsensusConfigSchema, ResearchDossier
from python.helpers.consensus_arbiter import ConsensusOrchestrator
from python.helpers.consensus_integration import ResearchPipeline
from python.helpers.consensus_mcp_integration import research_with_consensus


def _decision():
    return ConsensusDecision(
        proposal_id="p1",
        decision_hash="hash",
        status=ConsensusStatusEnum.NO_CONSENSUS,
        approved=False,
        votes={},
        vote_count=VoteCount(),
        decision_time_ms=1,
        correlation_id="corr",
        warnings=[],
    )


@pytest.mark.asyncio
async def test_consensus_orchestrator_delegates_to_engine():
    with patch("python.consensus.engine.run_consensus", new=AsyncMock(return_value=_decision())) as mocked:
        orchestrator = ConsensusOrchestrator()
        await orchestrator.seek_consensus(
            action="Test action",
            context={"k": "v"},
            correlation_id="corr",
        )
        assert mocked.called is True


@pytest.mark.asyncio
async def test_mcp_integration_delegates_to_engine():
    with patch("python.consensus.engine.run_consensus", new=AsyncMock(return_value=_decision())) as mocked:
        await research_with_consensus(
            query="Test query",
            mcp_handler=None,
            consensus_manager=None,
            call_llm_func=None,
            sources=["tavily"],
        )
        assert mocked.called is True


@pytest.mark.asyncio
async def test_consensus_integration_delegates_to_engine():
    with patch("python.consensus.engine.run_consensus", new=AsyncMock(return_value=_decision())) as mocked:
        pipeline = ResearchPipeline(consensus_config=ConsensusConfigSchema())
        dossier = ResearchDossier(
            dossier_id="d1",
            query="q1",
            created_at=time.time(),
        )
        await pipeline.validate_with_consensus(dossier, "final conclusion")
        assert mocked.called is True

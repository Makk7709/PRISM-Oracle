"""
Entrypoint delegation tests for PRISM consensus.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.consensus.engine import ConsensusDecision
from python.helpers.consensus_manager import VoteCount
from python.helpers.consensus_contracts import ConsensusStatusEnum
from python.helpers.consensus_arbiter import ConsensusOrchestrator


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

# NOTE (réalignement chemin critique, ADR-010 / Phase 9 cleanup) :
# les tests de délégation de `consensus_integration.ResearchPipeline` et
# `consensus_mcp_integration.research_with_consensus` ont été supprimés avec ces
# modules orphelins. La délégation vers l'API canonique `run_consensus` reste
# couverte par `test_consensus_orchestrator_delegates_to_engine` ci-dessus.

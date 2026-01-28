"""
Fail-soft envelope tests for consensus failures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.consensus.engine import ConsensusDecision, build_fail_soft_envelope
from python.helpers.consensus_manager import VoteCount
from python.helpers.consensus_contracts import ConsensusStatusEnum, ReliabilityTierEnum


def test_fail_soft_envelope_infra_failure():
    decision = ConsensusDecision(
        proposal_id="p1",
        decision_hash="hash",
        status=ConsensusStatusEnum.INFRA_FAILURE,
        approved=False,
        votes={},
        vote_count=VoteCount(),
        decision_time_ms=0,
        correlation_id="corr",
        warnings=["consensus_not_reached"],
    )

    envelope = build_fail_soft_envelope(
        answer="Draft response",
        decision=decision,
        unknowns=["Missing sources"],
        recommended_next_steps=["Collect sources"],
    )

    assert envelope.consensus.status == ConsensusStatusEnum.INFRA_FAILURE
    assert envelope.reliability_tiers[0].tier == ReliabilityTierEnum.LOW

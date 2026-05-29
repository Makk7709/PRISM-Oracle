"""
DEF-CM-1 regression test (audit hostile 29 mai 2026).

Garantit que `_finalize_proposal` est idempotent : deux invocations sur la
meme proposition ne doivent pas double-incrementer les metriques ni emettre
l'evenement consensus_reached deux fois.

Le defaut originel : `check_consensus()` a des effets de bord sur status et
`submit_vote` cree un asyncio.create_task(_finalize_proposal(...)) si
check_consensus renvoie True. Aucun garde n'empechait deux _finalize de
s'executer sur la meme proposition si appeles de l'exterieur ou via une
re-invocation accidentelle.

Ce test reproduit la sequence et verifie que le second _finalize est
no-op : memes metriques, un seul evenement.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
)


@pytest.mark.asyncio
async def test_finalize_proposal_idempotent_under_double_invocation():
    """Deux appels successifs a _finalize_proposal ne doivent pas double-compter."""
    manager = ConsensusManager(timeout_ms=60_000, total_providers=3)

    proposal_id = await manager.propose(
        decision_hash="hash-idem-1",
        payload={"action": "test"},
        decision_type=DecisionType.CRITICAL,
    )

    events = []
    manager.on("consensus_reached", lambda data: events.append(data))

    manager.submit_vote(proposal_id, "provider_a", VoteType.APPROVE, "ok")
    manager.submit_vote(proposal_id, "provider_b", VoteType.APPROVE, "ok")
    manager.submit_vote(proposal_id, "provider_c", VoteType.APPROVE, "ok")

    await asyncio.sleep(0.05)

    metrics_after_first = dict(manager.metrics)
    events_after_first = list(events)

    await manager._finalize_proposal(proposal_id)

    assert manager.metrics["approved_proposals"] == metrics_after_first["approved_proposals"], (
        "_finalize_proposal a double-compte approved_proposals "
        f"({metrics_after_first['approved_proposals']} -> {manager.metrics['approved_proposals']})"
    )
    assert len(events) == len(events_after_first), (
        f"_finalize_proposal a re-emis l'evenement consensus_reached "
        f"({len(events_after_first)} -> {len(events)})"
    )


@pytest.mark.asyncio
async def test_finalize_proposal_archives_only_once():
    """La proposition ne doit pas re-apparaitre dans self.proposals apres archivage."""
    manager = ConsensusManager(timeout_ms=60_000, total_providers=3)
    proposal_id = await manager.propose(
        decision_hash="hash-idem-2",
        payload={"action": "test"},
        decision_type=DecisionType.CRITICAL,
    )

    manager.submit_vote(proposal_id, "p1", VoteType.APPROVE, "")
    manager.submit_vote(proposal_id, "p2", VoteType.APPROVE, "")
    manager.submit_vote(proposal_id, "p3", VoteType.APPROVE, "")

    await asyncio.sleep(0.05)

    assert proposal_id not in manager.proposals
    assert proposal_id in manager.recent_proposals

    await manager._finalize_proposal(proposal_id)

    assert proposal_id not in manager.proposals
    assert proposal_id in manager.recent_proposals
    assert manager.recent_proposals[proposal_id].status == ConsensusStatus.APPROVED


@pytest.mark.asyncio
async def test_finalize_proposal_idempotent_under_concurrent_scheduling():
    """
    Scenario hostile : deux _finalize_proposal sont schedules avant que l'un
    n'archive la proposition. C'est le scenario reel de race (DEF-CM-1).
    Le statut/metriques ne doivent etre comptes qu'une seule fois.
    """
    manager = ConsensusManager(timeout_ms=60_000, total_providers=3)
    proposal_id = await manager.propose(
        decision_hash="hash-idem-3",
        payload={"action": "test"},
        decision_type=DecisionType.CRITICAL,
    )

    proposal = manager.proposals[proposal_id]
    proposal.add_vote("p1", VoteType.APPROVE, "")
    proposal.add_vote("p2", VoteType.APPROVE, "")
    proposal.add_vote("p3", VoteType.APPROVE, "")
    proposal.status = ConsensusStatus.APPROVED

    events = []
    manager.on("consensus_reached", lambda data: events.append(data))

    await asyncio.gather(
        manager._finalize_proposal(proposal_id),
        manager._finalize_proposal(proposal_id),
    )

    assert manager.metrics["approved_proposals"] == 1, (
        f"DEF-CM-1: _finalize_proposal a double-compte sous race "
        f"(expected=1, got={manager.metrics['approved_proposals']})"
    )
    assert len(events) == 1, (
        f"DEF-CM-1: consensus_reached emis {len(events)} fois (expected=1)"
    )

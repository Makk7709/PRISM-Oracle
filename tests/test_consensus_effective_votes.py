"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CONSENSUS EFFECTIVE VOTES — CANONICAL TEST CASES                   ║
║                                                                              ║
║  Tests for the corrected consensus logic that properly separates             ║
║  UNAVAILABLE (infrastructure signal) from effective votes.                   ║
║                                                                              ║
║  INVARIANTS TESTED:                                                          ║
║  1. UNAVAILABLE ≠ vote (never counts in quorum)                              ║
║  2. Zero effective votes ⇒ INFRA_FAILURE (not REJECTED)                      ║
║  3. Quorum calculated on effective votes only                                ║
║  4. Fail-closed ≠ lying (block without inventing a decision)                 ║
║  5. Every decision must be explainable by real tally                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from python.helpers.consensus_manager import (
    ConsensusStatus,
    VoteType,
    VoteCount,
    DecisionProposal,
    DecisionType,
)


# ═══════════════════════════════════════════════════════════════════════════════
# VOTE COUNT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoteCountEffectiveVotes:
    """Test VoteCount.effective_votes property."""
    
    def test_effective_votes_excludes_unavailable(self):
        """UNAVAILABLE should NOT count as effective vote."""
        count = VoteCount(
            approvals=1,
            rejections=1,
            abstentions=1,
            unavailable=5,
            total=8
        )
        assert count.effective_votes == 3  # 1+1+1, NOT 8
        assert count.unavailable == 5
        assert count.total == 8
    
    def test_effective_votes_all_unavailable(self):
        """All UNAVAILABLE should give 0 effective votes."""
        count = VoteCount(
            approvals=0,
            rejections=0,
            abstentions=0,
            unavailable=3,
            total=3
        )
        assert count.effective_votes == 0
    
    def test_effective_votes_includes_abstentions(self):
        """Abstentions ARE effective votes (arbiter evaluated content)."""
        count = VoteCount(
            approvals=0,
            rejections=0,
            abstentions=3,
            unavailable=0,
            total=3
        )
        assert count.effective_votes == 3
    
    def test_decisive_votes_excludes_abstentions(self):
        """Decisive votes = approve + reject only."""
        count = VoteCount(
            approvals=1,
            rejections=1,
            abstentions=1,
            unavailable=0,
            total=3
        )
        assert count.decisive_votes == 2  # 1+1, not 3


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL TEST CASES (from mission spec)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalConsensusScenarios:
    """
    Canonical test cases that MUST pass.
    These are the exact scenarios specified in the mission.
    """
    
    def _create_proposal(self, min_effective: int = 2, total: int = 3) -> DecisionProposal:
        """Helper to create a proposal."""
        return DecisionProposal(
            id="test-proposal",
            decision_hash="test-hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=total,
            min_effective_votes=min_effective,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # CASE 1: 3×UNAVAILABLE ⇒ INFRA_FAILURE
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_all_unavailable_gives_infra_failure(self):
        """
        3×UNAVAILABLE ⇒ INFRA_FAILURE (NOT REJECTED!)
        
        This is the critical bug fix: when all arbiters are unavailable,
        we must NOT claim they rejected. No evaluation happened.
        """
        proposal = self._create_proposal()
        proposal.add_vote("arbiter_1", VoteType.UNAVAILABLE, "timeout")
        proposal.add_vote("arbiter_2", VoteType.UNAVAILABLE, "error")
        proposal.add_vote("arbiter_3", VoteType.UNAVAILABLE, "connection failed")
        
        consensus_reached = proposal.check_consensus()
        
        assert consensus_reached is True
        assert proposal.status == ConsensusStatus.INFRA_FAILURE
        # CRITICAL: Must NOT be REJECTED
        assert proposal.status != ConsensusStatus.REJECTED
    
    # ─────────────────────────────────────────────────────────────────────────
    # CASE 2: 1 approve + 2 unavailable, min=2 ⇒ NO_CONSENSUS
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_one_approve_two_unavailable_gives_no_consensus(self):
        """
        1 approve + 2 unavailable ⇒ NO_CONSENSUS
        
        Only 1 effective vote, but min_effective_votes=2 required.
        Cannot approve or reject with insufficient votes.
        """
        proposal = self._create_proposal(min_effective=2)
        proposal.add_vote("arbiter_1", VoteType.APPROVE, "looks good")
        proposal.add_vote("arbiter_2", VoteType.UNAVAILABLE, "timeout")
        proposal.add_vote("arbiter_3", VoteType.UNAVAILABLE, "error")
        
        consensus_reached = proposal.check_consensus()
        
        assert consensus_reached is True
        assert proposal.status == ConsensusStatus.NO_CONSENSUS
        # CRITICAL: Must NOT be APPROVED (not enough votes)
        assert proposal.status != ConsensusStatus.APPROVED
    
    # ─────────────────────────────────────────────────────────────────────────
    # CASE 3: 2 approve + 1 unavailable ⇒ APPROVED
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_two_approve_one_unavailable_gives_approved(self):
        """
        2 approve + 1 unavailable ⇒ APPROVED
        
        2 effective votes, 2 approvals = 100% approval rate.
        Quorum of 2/3 of 2 = 2 is reached.
        """
        proposal = self._create_proposal(min_effective=2)
        proposal.add_vote("arbiter_1", VoteType.APPROVE, "approved")
        proposal.add_vote("arbiter_2", VoteType.APPROVE, "looks safe")
        proposal.add_vote("arbiter_3", VoteType.UNAVAILABLE, "timeout")
        
        consensus_reached = proposal.check_consensus()
        
        assert consensus_reached is True
        assert proposal.status == ConsensusStatus.APPROVED
    
    # ─────────────────────────────────────────────────────────────────────────
    # CASE 4: 2 reject + 1 unavailable ⇒ REJECTED
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_two_reject_one_unavailable_gives_rejected(self):
        """
        2 reject + 1 unavailable ⇒ REJECTED
        
        2 effective votes, 2 rejections = 100% rejection rate.
        This IS a real rejection based on actual evaluation.
        """
        proposal = self._create_proposal(min_effective=2)
        proposal.add_vote("arbiter_1", VoteType.REJECT, "risky action")
        proposal.add_vote("arbiter_2", VoteType.REJECT, "unsafe content")
        proposal.add_vote("arbiter_3", VoteType.UNAVAILABLE, "timeout")
        
        consensus_reached = proposal.check_consensus()
        
        assert consensus_reached is True
        assert proposal.status == ConsensusStatus.REJECTED
    
    # ─────────────────────────────────────────────────────────────────────────
    # CASE 5: 1 approve + 1 reject + 1 abstain ⇒ NO_CONSENSUS
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_split_vote_with_abstain_gives_no_consensus(self):
        """
        1 approve + 1 reject + 1 abstain ⇒ NO_CONSENSUS
        
        3 effective votes, but no 2/3 majority in either direction.
        """
        proposal = self._create_proposal(min_effective=2)
        proposal.add_vote("arbiter_1", VoteType.APPROVE, "looks ok")
        proposal.add_vote("arbiter_2", VoteType.REJECT, "uncertain")
        proposal.add_vote("arbiter_3", VoteType.ABSTAIN, "need more info")
        
        consensus_reached = proposal.check_consensus()
        
        assert consensus_reached is True
        assert proposal.status == ConsensusStatus.NO_CONSENSUS
    
    # ─────────────────────────────────────────────────────────────────────────
    # CASE 6: 1 approve + 1 abstain + 1 unavailable ⇒ NO_CONSENSUS
    # ─────────────────────────────────────────────────────────────────────────
    
    def test_one_approve_one_abstain_one_unavailable_gives_no_consensus(self):
        """
        1 approve + 1 abstain + 1 unavailable ⇒ NO_CONSENSUS
        
        2 effective votes (approve + abstain), but only 1 approval.
        Quorum of ceil(2/3 * 2) = 2 not reached.
        """
        proposal = self._create_proposal(min_effective=2)
        proposal.add_vote("arbiter_1", VoteType.APPROVE, "approve")
        proposal.add_vote("arbiter_2", VoteType.ABSTAIN, "not sure")
        proposal.add_vote("arbiter_3", VoteType.UNAVAILABLE, "timeout")
        
        consensus_reached = proposal.check_consensus()
        
        assert consensus_reached is True
        assert proposal.status == ConsensusStatus.NO_CONSENSUS


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT VERIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusInvariants:
    """Tests that verify the core invariants are never violated."""
    
    def _create_proposal(self, min_effective: int = 2, total: int = 3) -> DecisionProposal:
        """Helper to create a proposal."""
        return DecisionProposal(
            id="test-proposal",
            decision_hash="test-hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=total,
            min_effective_votes=min_effective,
        )
    
    def test_rejected_never_returned_without_rejections(self):
        """
        INVARIANT: REJECTED is NEVER returned without effective rejections.
        
        This is THE critical invariant that was violated before.
        """
        # All possible scenarios with 0 rejections
        scenarios = [
            # All unavailable
            [(VoteType.UNAVAILABLE,) * 3],
            # Mix of approve and unavailable
            [(VoteType.APPROVE, VoteType.UNAVAILABLE, VoteType.UNAVAILABLE)],
            [(VoteType.APPROVE, VoteType.APPROVE, VoteType.UNAVAILABLE)],
            # All approve
            [(VoteType.APPROVE, VoteType.APPROVE, VoteType.APPROVE)],
            # Mix with abstain
            [(VoteType.APPROVE, VoteType.ABSTAIN, VoteType.UNAVAILABLE)],
            [(VoteType.ABSTAIN, VoteType.ABSTAIN, VoteType.ABSTAIN)],
            [(VoteType.ABSTAIN, VoteType.UNAVAILABLE, VoteType.UNAVAILABLE)],
        ]
        
        for scenario in scenarios:
            votes = scenario[0]
            proposal = self._create_proposal()
            for i, vote in enumerate(votes):
                proposal.add_vote(f"arbiter_{i}", vote, f"vote_{i}")
            
            proposal.check_consensus()
            count = proposal.get_vote_count()
            
            # If there are no rejections, status MUST NOT be REJECTED
            if count.rejections == 0:
                assert proposal.status != ConsensusStatus.REJECTED, (
                    f"REJECTED returned with 0 rejections! Votes: {votes}"
                )
    
    def test_approved_never_returned_without_approvals(self):
        """
        INVARIANT: APPROVED is NEVER returned without effective approvals.
        """
        scenarios = [
            # All unavailable
            [(VoteType.UNAVAILABLE,) * 3],
            # Mix of reject and unavailable
            [(VoteType.REJECT, VoteType.UNAVAILABLE, VoteType.UNAVAILABLE)],
            [(VoteType.REJECT, VoteType.REJECT, VoteType.UNAVAILABLE)],
            # All reject
            [(VoteType.REJECT, VoteType.REJECT, VoteType.REJECT)],
            # Mix with abstain
            [(VoteType.REJECT, VoteType.ABSTAIN, VoteType.UNAVAILABLE)],
            [(VoteType.ABSTAIN, VoteType.ABSTAIN, VoteType.ABSTAIN)],
        ]
        
        for scenario in scenarios:
            votes = scenario[0]
            proposal = self._create_proposal()
            for i, vote in enumerate(votes):
                proposal.add_vote(f"arbiter_{i}", vote, f"vote_{i}")
            
            proposal.check_consensus()
            count = proposal.get_vote_count()
            
            # If there are no approvals, status MUST NOT be APPROVED
            if count.approvals == 0:
                assert proposal.status != ConsensusStatus.APPROVED, (
                    f"APPROVED returned with 0 approvals! Votes: {votes}"
                )
    
    def test_unavailable_never_contributes_to_quorum(self):
        """
        INVARIANT: UNAVAILABLE never contributes to quorum calculation.
        
        Even with 10 UNAVAILABLE votes, they don't help reach quorum.
        """
        proposal = DecisionProposal(
            id="test-proposal",
            decision_hash="test-hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=10,
            min_effective_votes=2,
        )
        
        # 1 approve + 9 unavailable
        proposal.add_vote("arbiter_0", VoteType.APPROVE, "approve")
        for i in range(1, 10):
            proposal.add_vote(f"arbiter_{i}", VoteType.UNAVAILABLE, "unavailable")
        
        proposal.check_consensus()
        
        # Despite 10 total responses, only 1 effective vote
        # Should be NO_CONSENSUS (min=2 required)
        assert proposal.status == ConsensusStatus.NO_CONSENSUS
    
    def test_zero_effective_votes_gives_infra_failure_not_rejected(self):
        """
        INVARIANT: Zero effective votes = INFRA_FAILURE, NEVER REJECTED.
        
        This is the core fix for the "0/0/TIMEOUT → REJECTED" bug.
        """
        for total in [1, 2, 3, 5, 10]:
            proposal = DecisionProposal(
                id="test-proposal",
                decision_hash="test-hash",
                payload={},
                type=DecisionType.CRITICAL,
                timestamp=0.0,
                total_providers=total,
                min_effective_votes=2,
            )
            
            # All unavailable
            for i in range(total):
                proposal.add_vote(f"arbiter_{i}", VoteType.UNAVAILABLE, "unavailable")
            
            proposal.check_consensus()
            
            assert proposal.status == ConsensusStatus.INFRA_FAILURE, (
                f"Expected INFRA_FAILURE with {total} unavailable, got {proposal.status}"
            )
            assert proposal.status != ConsensusStatus.REJECTED


# ═══════════════════════════════════════════════════════════════════════════════
# QUORUM CALCULATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuorumCalculation:
    """Test that quorum is calculated correctly on effective votes only."""
    
    def test_quorum_2_of_3_effective(self):
        """With 3 effective votes, quorum is ceil(2/3 * 3) = 2."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.APPROVE, "")
        proposal.add_vote("a2", VoteType.APPROVE, "")
        proposal.add_vote("a3", VoteType.REJECT, "")
        
        proposal.check_consensus()
        assert proposal.status == ConsensusStatus.APPROVED
    
    def test_quorum_2_of_2_effective(self):
        """With 2 effective votes, quorum is ceil(2/3 * 2) = 2."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.APPROVE, "")
        proposal.add_vote("a2", VoteType.APPROVE, "")
        proposal.add_vote("a3", VoteType.UNAVAILABLE, "")
        
        proposal.check_consensus()
        assert proposal.status == ConsensusStatus.APPROVED
    
    def test_one_approve_one_reject_one_unavailable_no_consensus(self):
        """1 approve + 1 reject + 1 unavailable = NO_CONSENSUS."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.APPROVE, "")
        proposal.add_vote("a2", VoteType.REJECT, "")
        proposal.add_vote("a3", VoteType.UNAVAILABLE, "")
        
        proposal.check_consensus()
        # 2 effective votes, need ceil(2/3*2)=2 for quorum
        # 1 approve, 1 reject, neither reaches 2
        assert proposal.status == ConsensusStatus.NO_CONSENSUS


# ═══════════════════════════════════════════════════════════════════════════════
# NON-REGRESSION: Normal operation should be unchanged
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalOperationUnchanged:
    """Verify that normal voting (no UNAVAILABLE) works as before."""
    
    def test_unanimous_approve(self):
        """3 approve ⇒ APPROVED (unchanged)."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.APPROVE, "")
        proposal.add_vote("a2", VoteType.APPROVE, "")
        proposal.add_vote("a3", VoteType.APPROVE, "")
        
        proposal.check_consensus()
        assert proposal.status == ConsensusStatus.APPROVED
    
    def test_unanimous_reject(self):
        """3 reject ⇒ REJECTED (unchanged)."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.REJECT, "")
        proposal.add_vote("a2", VoteType.REJECT, "")
        proposal.add_vote("a3", VoteType.REJECT, "")
        
        proposal.check_consensus()
        assert proposal.status == ConsensusStatus.REJECTED
    
    def test_two_thirds_approve(self):
        """2 approve + 1 reject ⇒ APPROVED (unchanged)."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.APPROVE, "")
        proposal.add_vote("a2", VoteType.APPROVE, "")
        proposal.add_vote("a3", VoteType.REJECT, "")
        
        proposal.check_consensus()
        assert proposal.status == ConsensusStatus.APPROVED
    
    def test_two_thirds_reject(self):
        """2 reject + 1 approve ⇒ REJECTED (unchanged)."""
        proposal = DecisionProposal(
            id="test",
            decision_hash="hash",
            payload={},
            type=DecisionType.CRITICAL,
            timestamp=0.0,
            total_providers=3,
            min_effective_votes=2,
        )
        proposal.add_vote("a1", VoteType.REJECT, "")
        proposal.add_vote("a2", VoteType.REJECT, "")
        proposal.add_vote("a3", VoteType.APPROVE, "")
        
        proposal.check_consensus()
        assert proposal.status == ConsensusStatus.REJECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

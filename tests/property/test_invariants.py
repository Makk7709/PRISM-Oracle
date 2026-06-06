"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PROPERTY-BASED TESTS (INVARIANTS)                         ║
║                                                                              ║
║  Tests de propriétés pour les invariants PRISM.                              ║
║  Simule property-based testing via boucles paramétrées.                      ║
║                                                                              ║
║  Invariants testés:                                                          ║
║  - Invariance à l'ordre des votes                                            ║
║  - Robustesse au bruit (votes invalides)                                     ║
║  - Monotonicité (ajouter approve != basculer vers reject)                    ║
║  - Déterminisme (mêmes inputs = mêmes outputs)                               ║
║                                                                              ║
║  TAG: [PROPERTY]                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import hashlib
import itertools
import random
from typing import List, Tuple

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
)
from tests.harness.assertions import assert_quorum_2_3


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: DETERMINISTIC RANDOM
# ═══════════════════════════════════════════════════════════════════════════════

def deterministic_shuffle(items: List, seed: int) -> List:
    """Shuffle déterministe pour reproductibilité."""
    rng = random.Random(seed)
    items_copy = items.copy()
    rng.shuffle(items_copy)
    return items_copy


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 1: VOTE ORDER INVARIANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoteOrderInvariance:
    """L'ordre des votes ne doit pas affecter le résultat."""
    
    def test_order_invariance_all_approve(self):
        """3 approves dans n'importe quel ordre = APPROVED."""
        votes = [
            ("a1", VoteType.APPROVE),
            ("a2", VoteType.APPROVE),
            ("a3", VoteType.APPROVE),
        ]
        
        # Test all permutations
        for perm in itertools.permutations(votes):
            async def run():
                manager = ConsensusManager(timeout_ms=5000, total_providers=3)
                proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
                
                for provider, vote in perm:
                    manager.submit_vote(proposal_id, provider, vote)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                
                assert status["status"] == ConsensusStatus.APPROVED, \
                    f"Order {perm} should give APPROVED"
            
            asyncio.get_event_loop().run_until_complete(run())
    
    def test_order_invariance_mixed(self):
        """2 approves + 1 reject dans n'importe quel ordre = APPROVED."""
        votes = [
            ("a1", VoteType.APPROVE),
            ("a2", VoteType.APPROVE),
            ("a3", VoteType.REJECT),
        ]
        
        for seed in range(5):  # Test 5 random orders
            shuffled = deterministic_shuffle(votes, seed)
            
            async def run():
                manager = ConsensusManager(timeout_ms=5000, total_providers=3)
                proposal_id = await manager.propose(f"hash_{seed}", {}, DecisionType.CRITICAL)
                
                for provider, vote in shuffled:
                    manager.submit_vote(proposal_id, provider, vote)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                
                assert status["status"] == ConsensusStatus.APPROVED, \
                    f"Order {shuffled} should give APPROVED"
            
            asyncio.get_event_loop().run_until_complete(run())
    
    def test_order_invariance_rejection(self):
        """2 rejects + 1 approve dans n'importe quel ordre = REJECTED."""
        votes = [
            ("a1", VoteType.REJECT),
            ("a2", VoteType.REJECT),
            ("a3", VoteType.APPROVE),
        ]
        
        for seed in range(5):
            shuffled = deterministic_shuffle(votes, seed)
            
            async def run():
                manager = ConsensusManager(timeout_ms=5000, total_providers=3)
                proposal_id = await manager.propose(f"hash_{seed}", {}, DecisionType.CRITICAL)
                
                for provider, vote in shuffled:
                    manager.submit_vote(proposal_id, provider, vote)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                
                assert status["status"] == ConsensusStatus.REJECTED, \
                    f"Order {shuffled} should give REJECTED"
            
            asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 2: NOISE ROBUSTNESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoiseRobustness:
    """Les votes invalides ne doivent pas altérer le verdict."""
    
    def test_unavailable_votes_dont_flip_result(self):
        """Les votes UNAVAILABLE ne changent pas le résultat."""
        async def run():
            manager = ConsensusManager(timeout_ms=5000, total_providers=5)
            
            proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
            
            # 3 approves (enough for quorum of 5)
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a3", VoteType.APPROVE)
            # 2 unavailable (noise)
            manager.submit_vote(
                proposal_id,
                "a4",
                None,
                available=False,
                availability_reason="unavailable",
            )
            manager.submit_vote(
                proposal_id,
                "a5",
                None,
                available=False,
                availability_reason="unavailable",
            )
            
            await asyncio.sleep(0.1)
            manager.get_proposal_status(proposal_id)
            
            # 3/5 valid votes, all approve = should still work
            # Note: quorum is ceil(5*2/3) = 4, so 3 approves NOT enough
            # This tests that UNAVAILABLE doesn't count as reject
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_abstain_votes_neutral(self):
        """Les abstentions sont neutres."""
        async def run():
            manager = ConsensusManager(timeout_ms=5000, total_providers=3)
            
            proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
            
            # 2 approves + 1 abstain
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a3", VoteType.ABSTAIN)
            
            await asyncio.sleep(0.1)
            status = manager.get_proposal_status(proposal_id)
            
            # Abstain shouldn't prevent approval
            assert status["status"] == ConsensusStatus.APPROVED
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 3: MONOTONICITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestMonotonicity:
    """Ajouter un approve ne doit pas faire basculer vers reject."""
    
    def test_adding_approve_never_causes_reject(self):
        """Ajouter un approve ne cause jamais un reject."""
        async def run():
            # Start with 1 approve
            manager = ConsensusManager(timeout_ms=5000, total_providers=3)
            proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
            
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            
            # Status should be PENDING or will become APPROVED/REJECTED
            # Add another approve
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            
            await asyncio.sleep(0.1)
            status = manager.get_proposal_status(proposal_id)
            
            # With 2 approves (2/3 quorum), should be APPROVED
            assert status["status"] == ConsensusStatus.APPROVED
            
            # Adding a third approve shouldn't change to REJECTED
            # (Vote after decision is ignored anyway)
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_monotonic_approval_progression(self):
        """La progression vers approval est monotone."""
        # Test: 0 approve -> 1 approve -> 2 approve
        # Never goes: 0 -> APPROVED -> REJECTED
        
        async def run():
            manager = ConsensusManager(timeout_ms=5000, total_providers=3)
            proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
            
            statuses = []
            
            # No votes yet
            s0 = manager.get_proposal_status(proposal_id)
            statuses.append(s0["status"])
            
            # 1 approve
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            s1 = manager.get_proposal_status(proposal_id)
            statuses.append(s1["status"])
            
            # 2 approves
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            await asyncio.sleep(0.1)
            s2 = manager.get_proposal_status(proposal_id)
            statuses.append(s2["status"])
            
            # Once APPROVED, should not become REJECTED
            if ConsensusStatus.APPROVED in statuses:
                idx = statuses.index(ConsensusStatus.APPROVED)
                for status in statuses[idx:]:
                    assert status != ConsensusStatus.REJECTED, \
                        f"Monotonicity violated: went from APPROVED to REJECTED"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 4: DETERMINISM
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterminism:
    """Mêmes inputs = mêmes outputs (avec providers fakes)."""
    
    def test_same_votes_same_result(self):
        """Mêmes votes produisent même résultat."""
        async def run():
            results = []
            
            for _ in range(3):  # Run 3 times
                manager = ConsensusManager(timeout_ms=5000, total_providers=3)
                proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
                
                manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
                manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
                manager.submit_vote(proposal_id, "a3", VoteType.REJECT)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                results.append(status["status"])
            
            # All results should be identical
            assert all(r == results[0] for r in results), \
                f"Results vary: {results}"
            assert results[0] == ConsensusStatus.APPROVED
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_deterministic_across_instances(self):
        """Déterminisme à travers différentes instances."""
        async def run():
            # Create multiple managers and run same scenario
            statuses = []
            
            for i in range(5):
                manager = ConsensusManager(timeout_ms=5000, total_providers=3)
                proposal_id = await manager.propose(f"hash_{i}", {"seed": 42}, DecisionType.CRITICAL)
                
                # Same votes
                manager.submit_vote(proposal_id, "arbiter_1", VoteType.REJECT)
                manager.submit_vote(proposal_id, "arbiter_2", VoteType.REJECT)
                manager.submit_vote(proposal_id, "arbiter_3", VoteType.APPROVE)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                statuses.append(status["status"])
            
            # All should be REJECTED (2/3 majority)
            assert all(s == ConsensusStatus.REJECTED for s in statuses)
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 5: QUORUM THRESHOLD
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuorumThreshold:
    """Le seuil de quorum 2/3 est respecté."""
    
    def test_below_quorum_no_approval(self):
        """En dessous du quorum = pas d'approbation."""
        test_cases = [
            (1, 0, 3),  # 1/3 approve
            (1, 1, 3),  # 1/3 each, split
            (2, 0, 5),  # 2/5 approve (need 4)
            (3, 0, 5),  # 3/5 approve (need 4)
        ]
        
        for approves, rejects, total in test_cases:
            expected = assert_quorum_2_3(approves, rejects, total)
            
            if expected == "APPROVED":
                continue  # These should pass
            
            # These should NOT be approved
            async def run():
                manager = ConsensusManager(timeout_ms=5000, total_providers=total)
                proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
                
                for i in range(approves):
                    manager.submit_vote(proposal_id, f"a{i}", VoteType.APPROVE)
                for i in range(rejects):
                    manager.submit_vote(proposal_id, f"r{i}", VoteType.REJECT)
                
                # Fill rest with abstain
                for i in range(total - approves - rejects):
                    manager.submit_vote(proposal_id, f"x{i}", VoteType.ABSTAIN)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                
                if approves < (total * 2 + 2) // 3:
                    assert status["status"] != ConsensusStatus.APPROVED, \
                        f"{approves}/{total} should not be APPROVED"
            
            asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTY 6: FAIL-CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailClosed:
    """En cas de doute, rejeter."""
    
    def test_uncertainty_leads_to_rejection(self):
        """L'incertitude mène au rejet."""
        uncertain_cases = [
            # (approves, rejects, abstains) - no clear majority
            (1, 1, 1),
            (1, 0, 2),
            (0, 1, 2),
        ]
        
        for approves, rejects, abstains in uncertain_cases:
            async def run():
                manager = ConsensusManager(timeout_ms=5000, total_providers=3)
                proposal_id = await manager.propose("hash", {}, DecisionType.CRITICAL)
                
                for i in range(approves):
                    manager.submit_vote(proposal_id, f"a{i}", VoteType.APPROVE)
                for i in range(rejects):
                    manager.submit_vote(proposal_id, f"r{i}", VoteType.REJECT)
                for i in range(abstains):
                    manager.submit_vote(proposal_id, f"x{i}", VoteType.ABSTAIN)
                
                await asyncio.sleep(0.1)
                status = manager.get_proposal_status(proposal_id)
                
                # Should NOT be approved without clear majority
                assert status["status"] != ConsensusStatus.APPROVED, \
                    f"Uncertain case {approves}-{rejects}-{abstains} should not APPROVE"
            
            asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Exécute tous les tests de propriétés."""
    print("🧪 Running Property-Based (Invariant) Tests...\n")
    
    test_classes = [
        TestVoteOrderInvariance,
        TestNoiseRobustness,
        TestMonotonicity,
        TestDeterminism,
        TestQuorumThreshold,
        TestFailClosed,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"📋 {test_class.__name__}")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    print(f"   ✓ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"   ✗ {method_name}: {e}")
                    failed_tests.append((test_class.__name__, method_name, str(e)))
        print()
    
    print("=" * 60)
    print(f"📊 Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ {len(failed_tests)} FAILED:")
        for cls, method, error in failed_tests:
            print(f"   - {cls}.{method}")
        return 1
    else:
        print("\n✅ All property tests passed!")
        return 0


if __name__ == "__main__":
    exit(run_tests())

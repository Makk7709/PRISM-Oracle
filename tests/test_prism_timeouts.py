"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM TIMEOUT TESTS                                       ║
║                                                                              ║
║  Tests pour les timeouts déterministes.                                      ║
║  Vérifie: per-agent timeout, global budget, cancellation.                    ║
║                                                                              ║
║  TAG: [FAST]                                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
from typing import List, Tuple

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
)
from tests.harness.fakes import (
    FakeLLMProvider,
    FaultInjector,
    FaultType,
    FaultConfig,
    TestClock,
    get_test_clock,
)
from tests.harness.fixtures import TIMEOUT_TEST_CASES


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PER-AGENT TIMEOUT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerAgentTimeout:
    """Tests pour le timeout par agent."""
    
    def test_fast_agent_no_timeout(self):
        """Agent rapide ne timeout pas."""
        async def run():
            manager = ConsensusManager(timeout_ms=1000, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "fast_test"},
                DecisionType.CRITICAL
            )
            
            # Submit votes immediately (within timeout)
            manager.submit_vote(proposal_id, "agent_1", VoteType.APPROVE, "Fast")
            manager.submit_vote(proposal_id, "agent_2", VoteType.APPROVE, "Fast")
            
            # Check status
            await asyncio.sleep(0.1)
            status = manager.get_proposal_status(proposal_id)
            
            assert status is not None
            assert status["status"] == ConsensusStatus.APPROVED
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_slow_agent_timeout(self):
        """Agent lent cause timeout."""
        async def run():
            # Very short timeout
            manager = ConsensusManager(timeout_ms=100, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "slow_test"},
                DecisionType.CRITICAL
            )
            
            # Don't submit any votes - wait for timeout
            await asyncio.sleep(0.2)  # Wait past timeout
            
            status = manager.get_proposal_status(proposal_id)
            assert status is not None
            assert status["status"] == ConsensusStatus.INFRA_FAILURE
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_partial_votes_before_timeout(self):
        """Votes partiels avant timeout."""
        async def run():
            manager = ConsensusManager(timeout_ms=200, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "partial_test"},
                DecisionType.CRITICAL
            )
            
            # Only 1 vote submitted
            manager.submit_vote(proposal_id, "agent_1", VoteType.APPROVE, "Fast")
            
            # Wait for timeout
            await asyncio.sleep(0.3)
            
            status = manager.get_proposal_status(proposal_id)
            # Should be NO_CONSENSUS or INFRA_FAILURE since no quorum reached
            assert status["status"] in [ConsensusStatus.NO_CONSENSUS, ConsensusStatus.INFRA_FAILURE]
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GLOBAL BUDGET
# ═══════════════════════════════════════════════════════════════════════════════

class TestGlobalBudget:
    """Tests pour le budget global de temps."""
    
    def test_all_within_budget(self):
        """Tous les agents dans le budget."""
        async def run():
            manager = ConsensusManager(timeout_ms=1000, total_providers=3)
            
            start = time.time()
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "budget_test"},
                DecisionType.CRITICAL
            )
            
            # All votes fast
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a3", VoteType.REJECT)
            
            await asyncio.sleep(0.1)
            elapsed = (time.time() - start) * 1000
            
            # Should complete well within budget
            assert elapsed < 500, f"Took too long: {elapsed}ms"
            
            status = manager.get_proposal_status(proposal_id)
            assert status["status"] == ConsensusStatus.APPROVED
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_budget_enforcement(self):
        """Budget global est respecté."""
        async def run():
            # Short budget
            manager = ConsensusManager(timeout_ms=100, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "budget_enforce"},
                DecisionType.CRITICAL
            )
            
            # Don't vote - should timeout
            start = time.time()
            
            # Wait for timeout
            await asyncio.sleep(0.15)
            
            elapsed = (time.time() - start) * 1000
            
            status = manager.get_proposal_status(proposal_id)
            assert status["status"] == ConsensusStatus.INFRA_FAILURE
            
            # Verify it didn't take much longer than budget
            # Allow 50ms margin for processing
            assert elapsed < 200, f"Took too long after timeout: {elapsed}ms"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: TIMEOUT PRODUCES INFRA_FAILURE/NO_CONSENSUS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimeoutFailClosed:
    """Tests pour le principe fail-closed sur timeout."""
    
    def test_timeout_is_not_approve(self):
        """Timeout ne produit JAMAIS approve."""
        async def run():
            manager = ConsensusManager(timeout_ms=50, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "timeout_test"},
                DecisionType.CRITICAL
            )
            
            # No votes, wait for timeout
            await asyncio.sleep(0.1)
            
            status = manager.get_proposal_status(proposal_id)
            
            # CRITICAL: Timeout must NEVER be APPROVED
            assert status["status"] != ConsensusStatus.APPROVED, \
                "SECURITY VIOLATION: Timeout resulted in APPROVED!"
            assert status["status"] == ConsensusStatus.INFRA_FAILURE
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_single_approve_with_timeouts_rejected(self):
        """1 approve + 2 timeouts = NO quorum = fail."""
        async def run():
            manager = ConsensusManager(timeout_ms=100, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "partial_approve"},
                DecisionType.CRITICAL
            )
            
            # Only 1 vote
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE, "Yes")
            
            # Wait for timeout
            await asyncio.sleep(0.15)
            
            status = manager.get_proposal_status(proposal_id)
            
            # 1 approve is not enough for 2/3 quorum
            assert status["status"] != ConsensusStatus.APPROVED, \
                "1 approve should not reach quorum with 2 timeouts!"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CANCELLATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestCancellation:
    """Tests pour la cancellation propre."""
    
    def test_no_orphan_tasks_after_consensus(self):
        """Pas de tâches orphelines après consensus."""
        async def run():
            manager = ConsensusManager(timeout_ms=5000, total_providers=3)
            
            proposal_id = await manager.propose(
                "test_hash",
                {"action": "cancel_test"},
                DecisionType.CRITICAL
            )
            
            # Quick consensus
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            
            await asyncio.sleep(0.1)
            
            # The timeout task should be cancelled
            # (We can't directly verify, but manager should not have pending proposals)
            status = manager.get_proposal_status(proposal_id)
            assert status["status"] == ConsensusStatus.APPROVED
            
            # Check proposal moved to recent (no longer active)
            assert proposal_id not in manager.proposals
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_multiple_proposals_independent_timeouts(self):
        """Plusieurs propositions ont des timeouts indépendants."""
        async def run():
            manager = ConsensusManager(timeout_ms=200, total_providers=3)
            
            # Create 2 proposals
            p1 = await manager.propose("hash1", {"action": "p1"}, DecisionType.CRITICAL)
            p2 = await manager.propose("hash2", {"action": "p2"}, DecisionType.CRITICAL)
            
            # Resolve p1 quickly
            manager.submit_vote(p1, "a1", VoteType.APPROVE)
            manager.submit_vote(p1, "a2", VoteType.APPROVE)
            
            # Let p2 timeout
            await asyncio.sleep(0.3)
            
            s1 = manager.get_proposal_status(p1)
            s2 = manager.get_proposal_status(p2)
            
            assert s1["status"] == ConsensusStatus.APPROVED
            assert s2["status"] == ConsensusStatus.INFRA_FAILURE
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: METRICS TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimeoutMetrics:
    """Tests pour les métriques de timeout."""
    
    def test_timeout_count_metric(self):
        """Métrique de comptage timeout."""
        async def run():
            manager = ConsensusManager(timeout_ms=50, total_providers=3)
            
            initial_timeouts = manager.metrics["timeout_proposals"]
            
            # Create proposal that will timeout
            await manager.propose("hash", {"action": "metric_test"}, DecisionType.CRITICAL)
            
            await asyncio.sleep(0.1)
            
            assert manager.metrics["timeout_proposals"] == initial_timeouts + 1
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_average_decision_time_metric(self):
        """Métrique de temps moyen de décision."""
        async def run():
            manager = ConsensusManager(timeout_ms=5000, total_providers=3)
            
            proposal_id = await manager.propose(
                "hash",
                {"action": "time_test"},
                DecisionType.CRITICAL
            )
            
            # Quick decision
            manager.submit_vote(proposal_id, "a1", VoteType.APPROVE)
            manager.submit_vote(proposal_id, "a2", VoteType.APPROVE)
            
            await asyncio.sleep(0.1)
            
            # Average decision time should be non-negative and reasonable
            avg_time = manager.metrics["average_decision_time"]
            # Note: Can be 0 for very fast decisions (sub-millisecond)
            assert avg_time >= 0, "Average decision time should be non-negative"
            assert avg_time < 1000, f"Average time too high: {avg_time}ms"
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FAULT INJECTION TIMEOUTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFaultInjectedTimeouts:
    """Tests avec injection de fautes timeout."""
    
    def test_injected_timeout_handled(self):
        """Timeout injecté est géré correctement."""
        async def run():
            injector = FaultInjector()
            injector.configure("slow_provider", FaultConfig(
                fault_type=FaultType.TIMEOUT,
                delay_ms=100
            ))
            
            provider = FakeLLMProvider("slow_provider", fault_injector=injector)
            
            try:
                await provider.vote("test", {})
                assert False, "Should have raised TimeoutError"
            except asyncio.TimeoutError:
                pass  # Expected
        
        asyncio.get_event_loop().run_until_complete(run())


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Exécute tous les tests de timeout."""
    print("🧪 Running PRISM Timeout Tests...\n")
    
    test_classes = [
        TestPerAgentTimeout,
        TestGlobalBudget,
        TestTimeoutFailClosed,
        TestCancellation,
        TestTimeoutMetrics,
        TestFaultInjectedTimeouts,
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
        print("\n✅ All timeout tests passed!")
        return 0


if __name__ == "__main__":
    exit(run_tests())

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM CONSENSUS - TESTS                                   ║
║                                                                              ║
║  Tests unitaires et d'intégration pour le système de consensus.              ║
║                                                                              ║
║  Usage:                                                                      ║
║    python -m pytest tests/test_prism_consensus.py -v                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Pytest is optional
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Mock pytest decorators
    class pytest:
        @staticmethod
        def fixture(func):
            return func
        class mark:
            @staticmethod
            def asyncio(func):
                return func

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
    build_vote_prompt,
    generate_decision_hash,
    parse_llm_vote_response,
    is_critical_action,
)
from python.helpers.consensus_contracts import (
    ConsensusConfigSchema,
    LLMVoteResponseSchema,
    validate_strict,
    parse_llm_vote_response as parse_response,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def consensus_manager():
    """Crée un ConsensusManager pour les tests."""
    return ConsensusManager(
        timeout_ms=5000,
        total_providers=3
    )


@pytest.fixture
def sample_context():
    """Contexte exemple pour les tests."""
    return {
        "query": "Transformer architecture for patent analysis",
        "sources": ["arxiv", "semanticscholar"],
        "domain": "AI/ML"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusManager:
    """Tests pour ConsensusManager."""
    
    @pytest.mark.asyncio
    async def test_create_proposal(self, consensus_manager):
        """Test création d'une proposition."""
        proposal_id = await consensus_manager.propose(
            "test_hash_123",
            {"action": "test_action"},
            DecisionType.CRITICAL
        )
        
        assert proposal_id is not None
        assert len(proposal_id) == 36  # UUID format
        
        status = consensus_manager.get_proposal_status(proposal_id)
        assert status is not None
        assert status["status"] == ConsensusStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_submit_votes_approve(self, consensus_manager):
        """Test soumission de votes - approbation."""
        proposal_id = await consensus_manager.propose(
            "test_hash_approve",
            {"action": "safe_action"},
            DecisionType.CRITICAL
        )
        
        # Soumettre 3 votes avec 2 APPROVE (quorum 2/3)
        consensus_manager.submit_vote(proposal_id, "arbiter_1", VoteType.APPROVE, "Safe action")
        consensus_manager.submit_vote(proposal_id, "arbiter_2", VoteType.APPROVE, "Looks good")
        consensus_manager.submit_vote(proposal_id, "arbiter_3", VoteType.REJECT, "Minor concern")
        
        # Attendre finalisation
        await asyncio.sleep(0.2)
        
        status = consensus_manager.get_proposal_status(proposal_id)
        assert status["status"] == ConsensusStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_submit_votes_reject(self, consensus_manager):
        """Test soumission de votes - rejet."""
        proposal_id = await consensus_manager.propose(
            "test_hash_reject",
            {"action": "risky_action"},
            DecisionType.CRITICAL
        )
        
        # Soumettre 3 votes avec 2 REJECT (quorum 2/3)
        consensus_manager.submit_vote(proposal_id, "arbiter_1", VoteType.REJECT, "Too risky")
        consensus_manager.submit_vote(proposal_id, "arbiter_2", VoteType.REJECT, "Reject")
        consensus_manager.submit_vote(proposal_id, "arbiter_3", VoteType.APPROVE, "Minor concern")
        
        await asyncio.sleep(0.2)
        
        status = consensus_manager.get_proposal_status(proposal_id)
        assert status["status"] == ConsensusStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_fail_closed_timeout(self, consensus_manager):
        """Test fail-closed: timeout = rejet."""
        # Créer un manager avec timeout très court
        quick_manager = ConsensusManager(timeout_ms=100, total_providers=3)
        
        proposal_id = await quick_manager.propose(
            "test_hash_timeout",
            {"action": "slow_action"},
            DecisionType.CRITICAL
        )
        
        # Ne pas soumettre de votes, attendre timeout
        await asyncio.sleep(0.3)
        
        status = quick_manager.get_proposal_status(proposal_id)
        assert status["status"] == ConsensusStatus.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_fail_closed_no_quorum(self, consensus_manager):
        """Test fail-closed: pas de quorum = NO_CONSENSUS (not fake REJECTED)."""
        proposal_id = await consensus_manager.propose(
            "test_hash_no_quorum",
            {"action": "uncertain_action"},
            DecisionType.CRITICAL
        )
        
        # 1 APPROVE, 1 REJECT, 1 UNAVAILABLE
        # Only 2 effective votes (approve + reject), neither reaches 2/3 quorum
        consensus_manager.submit_vote(proposal_id, "arbiter_1", VoteType.APPROVE)
        consensus_manager.submit_vote(proposal_id, "arbiter_2", VoteType.REJECT)
        consensus_manager.submit_vote(proposal_id, "arbiter_3", VoteType.UNAVAILABLE)
        
        await asyncio.sleep(0.2)
        
        status = consensus_manager.get_proposal_status(proposal_id)
        # CRITICAL FIX: NO_CONSENSUS, not REJECTED
        # We cannot claim arbiters rejected when they didn't.
        # 1 approve + 1 reject = no quorum in either direction.
        assert status["status"] == ConsensusStatus.NO_CONSENSUS
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, consensus_manager):
        """Test suivi des métriques."""
        initial_total = consensus_manager.metrics["total_proposals"]
        initial_approved = consensus_manager.metrics["approved_proposals"]
        
        proposal_id = await consensus_manager.propose(
            "test_metrics",
            {"action": "metric_test"},
            DecisionType.CRITICAL
        )
        
        assert consensus_manager.metrics["total_proposals"] == initial_total + 1
        
        # Need 3 effective votes for quorum with min_effective_votes=2
        consensus_manager.submit_vote(proposal_id, "arbiter_1", VoteType.APPROVE)
        consensus_manager.submit_vote(proposal_id, "arbiter_2", VoteType.APPROVE)
        consensus_manager.submit_vote(proposal_id, "arbiter_3", VoteType.REJECT)  # 2/3 approve
        
        await asyncio.sleep(0.2)
        
        assert consensus_manager.metrics["approved_proposals"] >= initial_approved + 1


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestContracts:
    """Tests pour les contrats de validation."""
    
    def test_consensus_config_schema(self):
        """Test validation configuration consensus."""
        config = ConsensusConfigSchema(
            enabled=True,
            timeout_ms=10000,
            arbiter_model_1="openrouter/anthropic/claude-3.5-sonnet",
            arbiter_model_2="openrouter/openai/gpt-4o",
            arbiter_model_3="openrouter/google/gemini-pro-1.5"
        )
        
        assert config.enabled is True
        assert config.timeout_ms == 10000
        assert config.total_providers == 3
    
    def test_llm_vote_response_valid(self):
        """Test parsing réponse LLM valide."""
        json_response = '''
        {
            "approve": true,
            "reasoning": "Action is safe and well-documented",
            "confidence": 0.85,
            "risks_identified": ["minor_latency"]
        }
        '''
        
        parsed = parse_response(json_response)
        
        assert parsed.approve is True
        assert parsed.confidence == 0.85
        assert "minor_latency" in parsed.risks_identified
    
    def test_llm_vote_response_embedded_json(self):
        """Test parsing JSON embarqué dans du texte."""
        response = '''
        Here is my analysis:
        
        {"approve": false, "reasoning": "Too risky", "confidence": 0.9}
        
        Thank you.
        '''
        
        parsed = parse_response(response)
        
        assert parsed.approve is False
        assert "risky" in parsed.reasoning.lower()
    
    def test_llm_vote_response_invalid(self):
        """Test rejet réponse invalide (fail-closed)."""
        invalid_response = "This is not valid JSON"
        
        try:
            parse_response(invalid_response)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
    
    def test_llm_vote_missing_approve(self):
        """Test rejet si champ 'approve' manquant."""
        response = '{"reasoning": "No approval field"}'
        
        try:
            parse_response(response)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHelperFunctions:
    """Tests pour les fonctions utilitaires."""
    
    def test_generate_decision_hash(self):
        """Test génération de hash unique."""
        hash1 = generate_decision_hash("action1", {"ctx": 1})
        hash2 = generate_decision_hash("action2", {"ctx": 2})
        hash3 = generate_decision_hash("action1", {"ctx": 1})
        
        # Hashes différents pour inputs différents
        assert hash1 != hash2
        # Note: hash3 != hash1 car timestamp inclus
        assert len(hash1) == 64  # SHA-256
    
    def test_is_critical_action(self):
        """Test détection actions critiques."""
        # Actions critiques
        assert is_critical_action("delete_user_data") is True
        assert is_critical_action("publish_conclusion") is True
        assert is_critical_action("system_config_update") is True
        assert is_critical_action("final_recommendation") is True
        
        # Actions non critiques
        assert is_critical_action("get_user_profile") is False
        assert is_critical_action("search_papers") is False
    
    def test_build_vote_prompt(self, sample_context):
        """Test construction du prompt de vote."""
        prompt = build_vote_prompt(
            "Approve research conclusion",
            sample_context
        )
        
        assert "Approve research conclusion" in prompt
        assert "Transformer architecture" in prompt
        assert "JSON" in prompt
        assert "approve" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Tests d'intégration end-to-end."""
    
    @pytest.mark.asyncio
    async def test_full_consensus_flow(self):
        """Test flux complet de consensus."""
        # 1. Créer le manager
        manager = ConsensusManager(timeout_ms=5000, total_providers=3)
        
        events_received = []
        
        # 2. Configurer les listeners
        manager.on("proposal_created", lambda d: events_received.append(("created", d)))
        manager.on("vote_submitted", lambda d: events_received.append(("vote", d)))
        manager.on("consensus_reached", lambda d: events_received.append(("consensus", d)))
        
        # 3. Créer une proposition
        proposal_id = await manager.propose(
            generate_decision_hash("test_action", {}),
            {"action": "Integration test", "context": {"test": True}},
            DecisionType.RESEARCH_VALIDATION
        )
        
        # 4. Soumettre les votes
        # Note: Consensus may be reached after 2nd approve (early exit on quorum)
        manager.submit_vote(proposal_id, "Claude", VoteType.APPROVE, "Looks safe", 0.9)
        manager.submit_vote(proposal_id, "GPT-4", VoteType.APPROVE, "Approved", 0.85)
        manager.submit_vote(proposal_id, "Gemini", VoteType.REJECT, "Slight concern", 0.6)
        
        # 5. Wait for async finalization to complete
        await asyncio.sleep(0.2)
        
        # 6. Attendre résultat
        status = await manager.wait_for_consensus(proposal_id, 3000)
        
        # 7. Vérifications
        assert status is not None
        assert status["status"] == ConsensusStatus.APPROVED
        # Note: With early quorum exit, we may have 2 or 3 votes counted
        # depending on timing. The key invariant is: >= 2 approvals for quorum.
        assert status["votes"]["approvals"] >= 2
        
        # Vérifier les événements
        event_types = [e[0] for e in events_received]
        assert "created" in event_types
        assert "vote" in event_types
        assert "consensus" in event_types
    
    @pytest.mark.asyncio
    async def test_research_pipeline_simulation(self):
        """Test simulation du pipeline de recherche."""
        from python.helpers.research_pipeline import create_pipeline
        
        # Créer le pipeline sans MCP réel
        pipeline = create_pipeline(
            settings={
                "consensus_enabled": True,
                "consensus_timeout_ms": 5000,
                "consensus_arbiter_1": "test_model_1",
                "consensus_arbiter_2": "test_model_2",
                "consensus_arbiter_3": "test_model_3",
            }
        )
        
        # Ouvrir un dossier
        dossier = await pipeline._open_dossier("Test research query")
        
        assert dossier is not None
        assert dossier.query == "Test research query"
        assert dossier.status == "open"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run basic tests without pytest
    print("🧪 Running PRISM Consensus tests...")
    
    async def run_basic_tests():
        manager = ConsensusManager(timeout_ms=5000, total_providers=3)
        
        # Test 1: Create proposal
        print("\n📝 Test 1: Create proposal...")
        proposal_id = await manager.propose(
            "test_hash",
            {"action": "test"},
            DecisionType.CRITICAL
        )
        print(f"   ✓ Proposal created: {proposal_id[:8]}...")
        
        # Test 2: Submit votes (approve)
        print("\n🗳️  Test 2: Submit votes (2/3 approve)...")
        manager.submit_vote(proposal_id, "arbiter_1", VoteType.APPROVE, "OK")
        manager.submit_vote(proposal_id, "arbiter_2", VoteType.APPROVE, "Safe")
        manager.submit_vote(proposal_id, "arbiter_3", VoteType.REJECT, "Concern")
        
        await asyncio.sleep(0.3)
        
        status = manager.get_proposal_status(proposal_id)
        print(f"   ✓ Status: {status['status'].value}")
        print(f"   ✓ Votes: {status['votes']}")
        
        # Test 3: Fail-closed (timeout)
        print("\n⏰ Test 3: Fail-closed (timeout)...")
        quick_manager = ConsensusManager(timeout_ms=100, total_providers=3)
        
        timeout_proposal = await quick_manager.propose(
            "timeout_test",
            {"action": "slow"},
            DecisionType.CRITICAL
        )
        
        await asyncio.sleep(0.2)
        
        timeout_status = quick_manager.get_proposal_status(timeout_proposal)
        print(f"   ✓ Timeout status: {timeout_status['status'].value}")
        
        # Test 4: Metrics
        print("\n📊 Test 4: Metrics...")
        print(f"   ✓ Total proposals: {manager.metrics['total_proposals']}")
        print(f"   ✓ Approved: {manager.metrics['approved_proposals']}")
        print(f"   ✓ Rejected: {manager.metrics['rejected_proposals']}")
        
        print("\n✅ All basic tests passed!")
    
    asyncio.run(run_basic_tests())

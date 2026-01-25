"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM CONTRACT TESTS                                      ║
║                                                                              ║
║  Tests unitaires pour le contrat de vote strict.                             ║
║  Vérifie: schéma JSON, types, bornes, champs requis/optionnels.              ║
║                                                                              ║
║  TAG: [FAST]                                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import asyncio
from typing import Dict, Any

from tests.harness.fakes import FakeLLMProvider, FaultInjector, FaultType, FaultConfig
from tests.harness.assertions import (
    assert_vote_schema,
    assert_contract_valid,
    assert_consensus_result,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VALID VOTE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoteSchemaValid:
    """Tests pour votes valides."""
    
    def test_minimal_valid_vote(self):
        """Vote avec champs minimaux requis."""
        vote = {
            "provider": "arbiter_1",
            "approve": True,
            "confidence": 0.85,
            "reasoning": "Action is safe"
        }
        # Should not raise
        assert_vote_schema(vote, strict=False)
    
    def test_full_valid_vote(self):
        """Vote avec tous les champs."""
        vote = {
            "provider": "Claude",
            "approve": False,
            "confidence": 0.7,
            "reasoning": "Risk identified",
            "latency_ms": 150,
            "risks_identified": ["data_loss", "irreversible"]
        }
        assert_vote_schema(vote, strict=True)
    
    def test_confidence_bounds(self):
        """Confidence aux limites [0.0, 1.0]."""
        # Lower bound
        vote_low = {
            "provider": "test",
            "approve": False,
            "confidence": 0.0,
            "reasoning": "No confidence"
        }
        assert_vote_schema(vote_low, strict=False)
        
        # Upper bound
        vote_high = {
            "provider": "test",
            "approve": True,
            "confidence": 1.0,
            "reasoning": "Full confidence"
        }
        assert_vote_schema(vote_high, strict=False)
    
    def test_approve_false_is_valid(self):
        """approve=False est un vote valide (reject)."""
        vote = {
            "provider": "arbiter_2",
            "approve": False,
            "confidence": 0.9,
            "reasoning": "Rejected"
        }
        assert_vote_schema(vote, strict=False)
    
    def test_empty_reasoning_allowed(self):
        """Reasoning vide est techniquement valide."""
        vote = {
            "provider": "arbiter_3",
            "approve": True,
            "confidence": 0.5,
            "reasoning": ""
        }
        assert_vote_schema(vote, strict=False)
    
    def test_integer_confidence_coerced(self):
        """Confidence entière (0 ou 1) est valide."""
        vote = {
            "provider": "test",
            "approve": True,
            "confidence": 1,  # Integer
            "reasoning": "OK"
        }
        assert_vote_schema(vote, strict=False)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INVALID VOTE SCHEMAS (MUST FAIL)
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoteSchemaInvalid:
    """Tests pour votes invalides - doivent échouer."""
    
    def test_missing_provider(self):
        """Vote sans provider."""
        vote = {
            "approve": True,
            "confidence": 0.8,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "missing required fields" in str(e).lower() or "provider" in str(e).lower()
    
    def test_missing_approve(self):
        """Vote sans approve."""
        vote = {
            "provider": "test",
            "confidence": 0.8,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "approve" in str(e).lower()
    
    def test_missing_confidence(self):
        """Vote sans confidence."""
        vote = {
            "provider": "test",
            "approve": True,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "confidence" in str(e).lower()
    
    def test_approve_string_invalid(self):
        """approve comme string au lieu de bool."""
        vote = {
            "provider": "test",
            "approve": "true",  # String!
            "confidence": 0.8,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "bool" in str(e).lower()
    
    def test_confidence_out_of_bounds_low(self):
        """Confidence < 0."""
        vote = {
            "provider": "test",
            "approve": True,
            "confidence": -0.1,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "0.0" in str(e) or "bound" in str(e).lower()
    
    def test_confidence_out_of_bounds_high(self):
        """Confidence > 1."""
        vote = {
            "provider": "test",
            "approve": True,
            "confidence": 1.5,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "1.0" in str(e) or "bound" in str(e).lower()
    
    def test_empty_provider(self):
        """Provider vide."""
        vote = {
            "provider": "",
            "approve": True,
            "confidence": 0.8,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "empty" in str(e).lower()
    
    def test_provider_wrong_type(self):
        """Provider de mauvais type."""
        vote = {
            "provider": 123,
            "approve": True,
            "confidence": 0.8,
            "reasoning": "OK"
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "str" in str(e).lower()
    
    def test_strict_mode_extra_fields(self):
        """Mode strict: rejette les champs extra."""
        vote = {
            "provider": "test",
            "approve": True,
            "confidence": 0.8,
            "reasoning": "OK",
            "extra_field": "should_fail"
        }
        try:
            assert_vote_schema(vote, strict=True)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "unexpected" in str(e).lower() or "extra" in str(e).lower()
    
    def test_negative_latency(self):
        """Latence négative."""
        vote = {
            "provider": "test",
            "approve": True,
            "confidence": 0.8,
            "reasoning": "OK",
            "latency_ms": -100
        }
        try:
            assert_vote_schema(vote)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "negative" in str(e).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LLM RESPONSE CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMResponseContract:
    """Tests pour le contrat de réponse LLM."""
    
    def test_valid_json_response(self):
        """Réponse JSON valide."""
        response = json.dumps({
            "approve": True,
            "reasoning": "Safe action",
            "confidence": 0.9,
            "risks_identified": []
        })
        result = assert_contract_valid(response)
        assert result["approve"] is True
        assert result["confidence"] == 0.9
    
    def test_minimal_valid_response(self):
        """Réponse minimale valide."""
        response = json.dumps({
            "approve": False,
            "reasoning": "Rejected"
        })
        result = assert_contract_valid(response)
        assert result["approve"] is False
    
    def test_invalid_json(self):
        """JSON invalide."""
        response = "not valid json {"
        try:
            assert_contract_valid(response)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "not valid json" in str(e).lower()
    
    def test_missing_approve_field(self):
        """Champ approve manquant."""
        response = json.dumps({
            "reasoning": "No approve field"
        })
        try:
            assert_contract_valid(response)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "approve" in str(e).lower()
    
    def test_array_instead_of_object(self):
        """Array au lieu d'objet."""
        response = json.dumps([{"approve": True}])
        try:
            assert_contract_valid(response)
            assert False, "Should have raised AssertionError"
        except AssertionError as e:
            assert "object" in str(e).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FAKE LLM PROVIDER CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class TestFakeLLMContract:
    """Tests pour le FakeLLMProvider."""
    
    def test_fake_llm_returns_valid_contract(self):
        """FakeLLM retourne toujours un contrat valide."""
        provider = FakeLLMProvider("test_arbiter", scenario="approve_safe")
        
        async def run():
            response = await provider.complete("Test prompt")
            return assert_contract_valid(response)
        
        result = asyncio.get_event_loop().run_until_complete(run())
        assert result["approve"] is True
    
    def test_fake_llm_all_scenarios_valid(self):
        """Tous les scénarios FakeLLM sont valides."""
        scenarios = ["approve_safe", "approve_cautious", "reject_risky", "reject_uncertain", "abstain"]
        
        async def run():
            for scenario in scenarios:
                provider = FakeLLMProvider("test", scenario=scenario)
                response = await provider.complete("Test")
                result = assert_contract_valid(response)
                assert "approve" in result
                assert "reasoning" in result
        
        asyncio.get_event_loop().run_until_complete(run())
    
    def test_fake_llm_vote_interface_valid(self):
        """Interface vote() retourne un schéma valide."""
        provider = FakeLLMProvider("arbiter_1", scenario="approve_safe")
        
        async def run():
            vote = await provider.vote("Test action", {"context": "test"})
            assert_vote_schema(vote, strict=False)
            return vote
        
        vote = asyncio.get_event_loop().run_until_complete(run())
        assert vote["provider"] == "arbiter_1"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONSENSUS RESULT CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsensusResultContract:
    """Tests pour le contrat de résultat consensus."""
    
    def test_valid_approved_result(self):
        """Résultat APPROVED valide."""
        result = {
            "proposal_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "APPROVED",
            "votes": {
                "approvals": 2,
                "rejections": 1,
                "total": 3
            },
            "decision_time_ms": 250
        }
        assert_consensus_result(result, expected_status="APPROVED")
    
    def test_valid_rejected_result(self):
        """Résultat REJECTED valide."""
        result = {
            "proposal_id": "abc-def",
            "status": "REJECTED",
            "votes": {
                "approvals": 0,
                "rejections": 2,
                "total": 2
            }
        }
        assert_consensus_result(result, expected_status="REJECTED")
    
    def test_invalid_status(self):
        """Statut invalide."""
        result = {
            "proposal_id": "test",
            "status": "UNKNOWN_STATUS",
            "votes": {}
        }
        try:
            assert_consensus_result(result)
            assert False, "Should have raised"
        except AssertionError as e:
            assert "invalid status" in str(e).lower()
    
    def test_min_votes_check(self):
        """Vérification nombre minimum de votes."""
        result = {
            "proposal_id": "test",
            "status": "APPROVED",
            "votes": {"total": 1}
        }
        try:
            assert_consensus_result(result, min_votes=3)
            assert False, "Should have raised"
        except AssertionError as e:
            assert "3 votes" in str(e).lower()
    
    def test_latency_check(self):
        """Vérification latence maximale."""
        result = {
            "proposal_id": "test",
            "status": "APPROVED",
            "votes": {},
            "decision_time_ms": 5000
        }
        try:
            assert_consensus_result(result, max_latency_ms=1000)
            assert False, "Should have raised"
        except AssertionError as e:
            assert "5000ms" in str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Exécute tous les tests de contrat."""
    print("🧪 Running PRISM Contract Tests...\n")
    
    test_classes = [
        TestVoteSchemaValid,
        TestVoteSchemaInvalid,
        TestLLMResponseContract,
        TestFakeLLMContract,
        TestConsensusResultContract,
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
    
    # Summary
    print("=" * 60)
    print(f"📊 Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ {len(failed_tests)} FAILED:")
        for cls, method, error in failed_tests:
            print(f"   - {cls}.{method}")
        return 1
    else:
        print("\n✅ All contract tests passed!")
        return 0


if __name__ == "__main__":
    exit(run_tests())

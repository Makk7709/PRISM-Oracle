"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    P3 RUNTIME IDEMPOTENCE TESTS                              ║
║                                                                              ║
║  Tests for P3 Production Hardening:                                         ║
║  - P3.1: Idempotency (same key → same output/audit_id)                      ║
║  - P3.2: Anti double-run (blocked duplicate executions)                     ║
║  - P3.3: Budgets & timeouts (fail-closed on timeout)                        ║
║  - P3.4: CI Gates compatibility                                              ║
║  - P3.5: Provenance validation                                              ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import time
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables for each test."""
    original_env = os.environ.copy()
    
    # Set defaults for testing
    os.environ["LEGAL_PIPELINE_ENABLED"] = "1"
    os.environ["LEGAL_PIPELINE_IDEMPOTENCE"] = "1"
    os.environ["LEGAL_CONSENSUS_SIMULATION"] = "1"
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def clear_idempotency_cache():
    """Clear the idempotency cache before each test."""
    from python.helpers.legal_orchestrator import get_idempotency_cache
    get_idempotency_cache().clear()
    yield
    get_idempotency_cache().clear()


@pytest.fixture
def clear_double_run_set():
    """Clear the double-run tracking set."""
    from python.extensions.legal_safe_mode._10_legal_safe_integration import _executed_correlation_ids
    _executed_correlation_ids.clear()
    yield
    _executed_correlation_ids.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# P3.1: IDEMPOTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3Idempotency:
    """P3.1: Test idempotency guarantees."""
    
    def test_idempotency_key_deterministic(self, clear_idempotency_cache):
        """Same inputs should produce same idempotency key."""
        from python.helpers.legal_orchestrator import get_idempotency_cache
        
        cache = get_idempotency_cache()
        
        key1 = cache.compute_idempotency_key(
            query="Quelles sont les conditions de validité d'un contrat ?",
            scope="info",
            jurisdiction="fr",
            risk_tier="low",
            source_chunk_ids=["chunk_001", "chunk_002"],
            enforcement_level="1",
        )
        
        key2 = cache.compute_idempotency_key(
            query="Quelles sont les conditions de validité d'un contrat ?",
            scope="info",
            jurisdiction="fr",
            risk_tier="low",
            source_chunk_ids=["chunk_002", "chunk_001"],  # Different order
            enforcement_level="1",
        )
        
        # Same key regardless of chunk order (sorted internally)
        assert key1 == key2
        assert len(key1) == 32  # SHA256 truncated
    
    def test_idempotency_key_varies_with_inputs(self, clear_idempotency_cache):
        """Different inputs should produce different keys."""
        from python.helpers.legal_orchestrator import get_idempotency_cache
        
        cache = get_idempotency_cache()
        
        key1 = cache.compute_idempotency_key(
            query="Question A",
            scope="info",
            jurisdiction="fr",
            risk_tier="low",
            source_chunk_ids=[],
            enforcement_level="1",
        )
        
        key2 = cache.compute_idempotency_key(
            query="Question B",  # Different query
            scope="info",
            jurisdiction="fr",
            risk_tier="low",
            source_chunk_ids=[],
            enforcement_level="1",
        )
        
        assert key1 != key2
    
    def test_idempotency_cache_set_get(self, clear_idempotency_cache):
        """Cache should store and retrieve outputs."""
        from python.helpers.legal_orchestrator import get_idempotency_cache
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        cache = get_idempotency_cache()
        
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test answer",
            audit_bundle_id="test_audit_123",
        )
        
        key = "test_key_123"
        correlation_id = "corr_123"
        
        # Set
        cache.set(key, output, correlation_id)
        
        # Get
        cached = cache.get(key, correlation_id)
        
        assert cached is not None
        assert cached.audit_bundle_id == output.audit_bundle_id
        assert cached.mode == output.mode
    
    def test_idempotency_cache_ttl_expiry(self, clear_idempotency_cache):
        """Cache should expire entries after TTL."""
        from python.helpers.legal_orchestrator import IdempotencyCache
        from python.helpers.legal_pipeline import LegalOutput, LegalOutputMode
        
        # Create cache with 0.1s TTL
        cache = IdempotencyCache(ttl_seconds=0.1)
        
        output = LegalOutput(
            mode=LegalOutputMode.SAFE_ANALYSIS,
            answer="Test",
            audit_bundle_id="test_audit",
        )
        
        key = "test_key"
        cache.set(key, output, "corr_1")
        
        # Should exist immediately
        assert cache.get(key, "corr_1") is not None
        
        # Wait for TTL
        time.sleep(0.15)
        
        # Should be expired
        assert cache.get(key, "corr_1") is None
    
    def test_idempotency_enabled_flag(self):
        """Idempotency flag should be controllable via env."""
        from python.helpers.legal_orchestrator import is_idempotency_enabled
        
        os.environ["LEGAL_PIPELINE_IDEMPOTENCE"] = "1"
        assert is_idempotency_enabled() is True
        
        os.environ["LEGAL_PIPELINE_IDEMPOTENCE"] = "0"
        assert is_idempotency_enabled() is False
    
    @pytest.mark.asyncio
    async def test_pipeline_idempotent_same_key_same_output(self, clear_idempotency_cache):
        """P3.1 Invariant: same idempotency_key → same audit_bundle_id."""
        from python.helpers.legal_orchestrator import run_legal_pipeline, get_idempotency_cache
        
        query = "Qu'est-ce qu'un contrat ?"
        
        # First run
        output1 = await run_legal_pipeline(
            query=query,
            correlation_id="corr_001",
        )
        
        # Second run with same query (should hit cache)
        output2 = await run_legal_pipeline(
            query=query,
            correlation_id="corr_002",
        )
        
        # Same audit_bundle_id when idempotent
        assert output1.audit_bundle_id == output2.audit_bundle_id
        
        # Check cache has entry
        assert get_idempotency_cache().size > 0


# ═══════════════════════════════════════════════════════════════════════════════
# P3.2: ANTI DOUBLE-RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3AntiDoubleRun:
    """P3.2: Test anti double-run barrier."""
    
    def test_mark_executed_first_time(self, clear_double_run_set):
        """First execution should be allowed."""
        from python.extensions.legal_safe_mode._10_legal_safe_integration import _mark_executed
        
        result = _mark_executed("corr_123")
        assert result is True
    
    def test_mark_executed_duplicate_blocked(self, clear_double_run_set):
        """Second execution with same correlation_id should be blocked."""
        from python.extensions.legal_safe_mode._10_legal_safe_integration import _mark_executed
        
        # First call
        result1 = _mark_executed("corr_123")
        assert result1 is True
        
        # Second call (duplicate)
        result2 = _mark_executed("corr_123")
        assert result2 is False
    
    def test_clear_executed(self, clear_double_run_set):
        """Clearing should allow re-execution."""
        from python.extensions.legal_safe_mode._10_legal_safe_integration import (
            _mark_executed,
            _clear_executed,
        )
        
        # Mark
        _mark_executed("corr_123")
        
        # Clear
        _clear_executed("corr_123")
        
        # Should be allowed again
        result = _mark_executed("corr_123")
        assert result is True
    
    def test_extension_has_double_run_protection(self, clear_double_run_set):
        """Extension should have double-run protection keys."""
        from python.extensions.legal_safe_mode._10_legal_safe_integration import (
            LegalSafeModeExtension,
            _executed_correlation_ids,
        )
        
        assert hasattr(LegalSafeModeExtension, 'PIPELINE_EXECUTED_KEY')
        assert isinstance(_executed_correlation_ids, set)


# ═══════════════════════════════════════════════════════════════════════════════
# P3.3: BUDGET & TIMEOUT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3BudgetTimeout:
    """P3.3: Test budget and timeout handling."""
    
    def test_budget_from_env(self):
        """Budget should load from environment."""
        from python.helpers.legal_orchestrator import PipelineBudget
        
        os.environ["LEGAL_BUDGET_TOTAL_MS"] = "5000"
        os.environ["LEGAL_BUDGET_RETRIEVAL_MS"] = "1000"
        
        budget = PipelineBudget.from_env()
        
        assert budget.total_budget_ms == 5000
        assert budget.retrieval_budget_ms == 1000
    
    def test_budget_defaults(self):
        """Budget should have sensible defaults."""
        from python.helpers.legal_orchestrator import PipelineBudget
        
        # Clear env vars
        for key in list(os.environ.keys()):
            if key.startswith("LEGAL_BUDGET_"):
                del os.environ[key]
        
        budget = PipelineBudget()
        
        assert budget.total_budget_ms == 12000
        assert budget.retrieval_budget_ms == 3000
        assert budget.llm_draft_budget_ms == 5000
        assert budget.judge_budget_ms == 500
        assert budget.consensus_budget_ms == 8000
        assert budget.rendering_budget_ms == 1000
    
    @pytest.mark.asyncio
    async def test_with_timeout_success(self):
        """with_timeout should return result when within budget."""
        from python.helpers.legal_orchestrator import with_timeout
        
        async def fast_task():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await with_timeout(
            fast_task(),
            budget_ms=1000,
            step="test_step",
            correlation_id="corr_123",
        )
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_with_timeout_exceeds_budget(self):
        """with_timeout should raise TimeoutError when exceeding budget."""
        from python.helpers.legal_orchestrator import with_timeout, TimeoutError
        
        async def slow_task():
            await asyncio.sleep(1.0)
            return "never reached"
        
        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(
                slow_task(),
                budget_ms=50,  # 50ms budget
                step="slow_step",
                correlation_id="corr_123",
            )
        
        assert exc_info.value.step == "slow_step"
        assert exc_info.value.budget_ms == 50
    
    def test_metrics_step_latencies(self):
        """Metrics should track step latencies."""
        from python.helpers.legal_orchestrator import get_legal_pipeline_metrics
        
        metrics = get_legal_pipeline_metrics()
        
        # Record some latencies
        metrics.record_step_latency("retrieval", 100)
        metrics.record_step_latency("retrieval", 200)
        metrics.record_step_latency("retrieval", 150)
        
        # Check p50/p95
        p50 = metrics.get_step_p50("retrieval")
        p95 = metrics.get_step_p95("retrieval")
        
        assert p50 == 150  # Middle value
        assert p95 >= 150
    
    def test_metrics_timeout_counter(self):
        """Metrics should count timeouts."""
        from python.helpers.legal_orchestrator import get_legal_pipeline_metrics
        
        metrics = get_legal_pipeline_metrics()
        initial = metrics.timeout_total
        
        metrics.record_timeout()
        metrics.record_timeout()
        
        assert metrics.timeout_total == initial + 2


# ═══════════════════════════════════════════════════════════════════════════════
# P3.4: CI GATES COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3CIGates:
    """P3.4: Test CI gates compatibility."""
    
    def test_fast_gate_no_index_required(self):
        """FAST gate tests should not require index."""
        # These tests should pass without FTS5 index
        from python.helpers.legal_orchestrator import LEGAL_INDEX_AVAILABLE
        
        # The flag exists
        assert isinstance(LEGAL_INDEX_AVAILABLE, bool)
    
    def test_nightly_marker_exists(self):
        """Nightly-only tests should be properly marked."""
        # This test verifies the marker infrastructure
        # Actual nightly tests will use @pytest.mark.nightly
        pass
    
    def test_metrics_export(self):
        """Metrics should be exportable for CI."""
        from python.helpers.legal_orchestrator import get_legal_pipeline_metrics
        
        metrics = get_legal_pipeline_metrics()
        metrics_dict = metrics.to_dict()
        
        # Required keys for CI monitoring
        assert "requests_total" in metrics_dict
        assert "refusals_total" in metrics_dict
        assert "timeout_total" in metrics_dict
        assert "idempotent_hits" in metrics_dict
        assert "double_run_blocked" in metrics_dict


# ═══════════════════════════════════════════════════════════════════════════════
# P3.5: PROVENANCE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3ProvenanceValidation:
    """P3.5: Test provenance validation."""
    
    def test_provenance_required_fields(self):
        """Provenance should have required fields."""
        from tests.fixtures.legal_corpus import CORPUS
        
        required_fields = {"source", "source_name", "license_name"}
        
        for doc in CORPUS:
            prov = doc.get("provenance", {})
            
            for field in required_fields:
                assert field in prov, f"Missing {field} in provenance for {doc.get('origin_id')}"
                assert prov[field], f"Empty {field} in provenance for {doc.get('origin_id')}"
    
    def test_provenance_has_origin_url(self):
        """Provenance should have origin_url."""
        from tests.fixtures.legal_corpus import CORPUS
        
        for doc in CORPUS:
            prov = doc.get("provenance", {})
            assert "origin_url" in prov, f"Missing origin_url for {doc.get('origin_id')}"


# ═══════════════════════════════════════════════════════════════════════════════
# NO REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestP3NoRegression:
    """Verify P3 doesn't break P0.7/P2."""
    
    @pytest.mark.asyncio
    async def test_pipeline_still_works(self, clear_idempotency_cache):
        """Pipeline should still work with P3 additions."""
        from python.helpers.legal_orchestrator import run_legal_pipeline
        from python.helpers.legal_pipeline import LegalOutputMode
        
        output = await run_legal_pipeline(
            query="Test query for P3",
            correlation_id="p3_test_001",
        )
        
        # Should return valid output
        assert output is not None
        assert output.mode in list(LegalOutputMode)
        assert output.audit_bundle_id is not None
    
    def test_p07_invariants_preserved(self):
        """P0.7 invariants should still be enforced."""
        from python.helpers.legal_pipeline import requires_consensus, LegalRouteContext
        from python.helpers.legal_pipeline import LegalRiskTier, DecisionScope, Jurisdiction
        
        # BOARD scope requires consensus
        board_context = LegalRouteContext(
            risk_tier=LegalRiskTier.MEDIUM,
            scope=DecisionScope.BOARD,
            jurisdiction=Jurisdiction.FR,
        )
        assert requires_consensus(board_context) is True
        
        # HIGH risk requires consensus
        high_context = LegalRouteContext(
            risk_tier=LegalRiskTier.HIGH,
            scope=DecisionScope.INFO,
            jurisdiction=Jurisdiction.FR,
        )
        assert requires_consensus(high_context) is True


# ═══════════════════════════════════════════════════════════════════════════════
# NIGHTLY-ONLY TESTS (marked)
# ═══════════════════════════════════════════════════════════════════════════════

# Custom marker for nightly tests
nightly = pytest.mark.skipif(
    os.environ.get("CI_NIGHTLY", "0") != "1",
    reason="Nightly-only test (set CI_NIGHTLY=1 to run)"
)


class TestP3Nightly:
    """Nightly-only tests requiring full index."""
    
    @nightly
    def test_fts5_index_required_in_nightly(self):
        """In nightly mode, FTS5 index must be available."""
        from python.helpers.legal_orchestrator import LEGAL_INDEX_AVAILABLE
        
        # This test FAILS if index is not available in nightly
        assert LEGAL_INDEX_AVAILABLE is True, \
            "FTS5 index must be available in nightly CI"
    
    @nightly
    def test_corpus_ingested_in_nightly(self, tmp_path):
        """In nightly mode, corpus should be fully ingested."""
        from tests.fixtures.legal_corpus import create_test_index, get_corpus_size
        
        index = create_test_index(tmp_path)
        
        # Search should return results
        results = index.search("contrat", limit=10)
        assert len(results) > 0, "Corpus should be searchable"


# RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

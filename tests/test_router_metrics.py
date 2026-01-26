"""
Tests for Router Metrics module.

Validates:
- Divergence rate calculation
- Error rate limiting
- Would-block detection
- Stats export
"""

import pytest
import time

from python.helpers.router.metrics import RouterMetrics, RouterStats, DivergenceSample


class TestRouterMetrics:
    """Test RouterMetrics singleton and basic operations."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        RouterMetrics.reset()
    
    def test_singleton(self):
        """Metrics is a singleton."""
        m1 = RouterMetrics.get_instance()
        m2 = RouterMetrics.get_instance()
        assert m1 is m2
    
    def test_record_decision_basic(self):
        """Basic decision recording."""
        metrics = RouterMetrics.get_instance()
        
        metrics.record_decision(
            route_id="abc123",
            input_hash="hash123",
            router_verdict="proceed",
            router_intents=["finance", "multitask"],
            is_board_level=False,
            llm_profile="finance",
            latency_ms=0.5,
            execution_blocked=False,
        )
        
        stats = metrics.get_stats()
        assert stats.total_decisions == 1
        assert stats.total_divergences == 0
        assert stats.decisions_by_intent.get("finance") == 1
    
    def test_divergence_detection(self):
        """Detect divergence when LLM profile doesn't match router intents."""
        metrics = RouterMetrics.get_instance()
        
        # LLM chose 'sales' but router detected 'finance'
        metrics.record_decision(
            route_id="abc123",
            input_hash="hash123",
            router_verdict="proceed",
            router_intents=["finance", "multitask"],
            is_board_level=False,
            llm_profile="sales",  # Divergence!
            latency_ms=0.5,
            execution_blocked=False,
        )
        
        stats = metrics.get_stats()
        assert stats.total_divergences == 1
        assert stats.divergence_rate() == 1.0
        
        # Check sample was recorded
        samples = metrics.get_divergence_samples()
        assert len(samples) == 1
        assert samples[0].llm_profile == "sales"
        assert samples[0].router_intents == ["finance", "multitask"]
    
    def test_divergence_rate_by_intent(self):
        """Calculate divergence rate per intent."""
        metrics = RouterMetrics.get_instance()
        
        # 3 finance decisions, 1 divergent
        for i in range(3):
            metrics.record_decision(
                route_id=f"fin{i}",
                input_hash=f"hash{i}",
                router_verdict="proceed",
                router_intents=["finance"],
                is_board_level=False,
                llm_profile="finance" if i < 2 else "sales",  # 1 divergent
                latency_ms=0.5,
                execution_blocked=False,
            )
        
        stats = metrics.get_stats()
        assert stats.decisions_by_intent.get("finance") == 3
        assert stats.divergence_by_intent.get("finance") == 1
        assert abs(stats.divergence_rate("finance") - 0.333) < 0.01
    
    def test_would_block_tracking(self):
        """Track when router would have blocked but execution continued."""
        metrics = RouterMetrics.get_instance()
        
        # Router says NEEDS_CLARIFICATION but execution not blocked
        metrics.record_decision(
            route_id="abc123",
            input_hash="hash123",
            router_verdict="needs_clarification",
            router_intents=["legal_safe"],
            is_board_level=True,
            llm_profile="legal_safe",
            latency_ms=0.5,
            execution_blocked=False,  # Audit mode - not blocked
        )
        
        stats = metrics.get_stats()
        assert stats.total_would_block == 1
    
    def test_would_block_not_counted_when_blocked(self):
        """Don't count would_block when execution was actually blocked."""
        metrics = RouterMetrics.get_instance()
        
        metrics.record_decision(
            route_id="abc123",
            input_hash="hash123",
            router_verdict="needs_clarification",
            router_intents=["legal_safe"],
            is_board_level=True,
            llm_profile="legal_safe",
            latency_ms=0.5,
            execution_blocked=True,  # Enforcement mode - blocked
        )
        
        stats = metrics.get_stats()
        assert stats.total_would_block == 0


class TestErrorRateLimiting:
    """Test error recording with rate limiting."""
    
    def setup_method(self):
        RouterMetrics.reset()
    
    def test_error_recorded(self):
        """Errors are recorded."""
        metrics = RouterMetrics.get_instance()
        
        metrics.record_error(ValueError("test error"), "hash123")
        
        stats = metrics.get_stats()
        assert stats.total_errors == 1
    
    def test_error_rate_limiting(self):
        """Same error type is rate-limited."""
        metrics = RouterMetrics.get_instance()
        
        # First error is logged
        logged1 = metrics.record_error(ValueError("test error"), "hash1")
        assert logged1 is True
        
        # Same error type immediately after is rate-limited
        logged2 = metrics.record_error(ValueError("test error"), "hash2")
        assert logged2 is False
        
        # Count still increases
        stats = metrics.get_stats()
        assert stats.total_errors == 2


class TestRouterStats:
    """Test RouterStats calculations."""
    
    def test_divergence_rate_empty(self):
        """Divergence rate is 0 when no decisions."""
        stats = RouterStats()
        assert stats.divergence_rate() == 0.0
    
    def test_error_rate_empty(self):
        """Error rate is 0 when no decisions or errors."""
        stats = RouterStats()
        assert stats.error_rate() == 0.0
    
    def test_to_dict(self):
        """Stats export to dict."""
        stats = RouterStats(
            total_decisions=100,
            total_divergences=5,
            total_errors=2,
            total_would_block=3,
            decisions_by_intent={"finance": 50, "legal_safe": 50},
            divergence_by_intent={"finance": 3, "legal_safe": 2},
            avg_latency_ms=0.5,
            max_latency_ms=2.0,
        )
        
        d = stats.to_dict()
        
        assert d["total_decisions"] == 100
        assert d["divergence_rate"] == 0.05
        assert d["error_rate"] == pytest.approx(0.0196, rel=0.01)
        assert "divergence_by_intent" in d


class TestDivergenceSampling:
    """Test divergence sample collection."""
    
    def setup_method(self):
        RouterMetrics.reset()
    
    def test_max_samples_respected(self):
        """Only last N divergence samples are kept."""
        metrics = RouterMetrics.get_instance()
        
        # Record 30 divergent decisions (max is 20)
        for i in range(30):
            metrics.record_decision(
                route_id=f"route{i}",
                input_hash=f"hash{i}",
                router_verdict="proceed",
                router_intents=["finance"],
                is_board_level=False,
                llm_profile="sales",  # Always divergent
                latency_ms=0.5,
                execution_blocked=False,
            )
        
        samples = metrics.get_divergence_samples()
        
        # Should only have last 20
        assert len(samples) == 20
        
        # First sample should be from iteration 10 (0-9 evicted)
        assert samples[0].input_hash == "hash10"
    
    def test_sample_contains_no_pii(self):
        """Samples contain hashes, not raw prompts."""
        metrics = RouterMetrics.get_instance()
        
        metrics.record_decision(
            route_id="abc123",
            input_hash="sha256hash",  # Hash, not raw text
            router_verdict="proceed",
            router_intents=["finance"],
            is_board_level=False,
            llm_profile="sales",
            latency_ms=0.5,
            execution_blocked=False,
        )
        
        samples = metrics.get_divergence_samples()
        assert len(samples) == 1
        
        # Sample has hash, not raw prompt
        sample = samples[0]
        assert sample.input_hash == "sha256hash"
        # No raw prompt field exists
        assert not hasattr(sample, "prompt")
        assert not hasattr(sample, "message")


class TestLatencyTracking:
    """Test latency metric collection."""
    
    def setup_method(self):
        RouterMetrics.reset()
    
    def test_avg_latency(self):
        """Average latency is calculated correctly."""
        metrics = RouterMetrics.get_instance()
        
        for latency in [0.1, 0.2, 0.3, 0.4, 0.5]:
            metrics.record_decision(
                route_id="route",
                input_hash="hash",
                router_verdict="proceed",
                router_intents=["finance"],
                is_board_level=False,
                llm_profile="finance",
                latency_ms=latency,
                execution_blocked=False,
            )
        
        stats = metrics.get_stats()
        assert stats.avg_latency_ms == pytest.approx(0.3, rel=0.01)
        assert stats.max_latency_ms == 0.5

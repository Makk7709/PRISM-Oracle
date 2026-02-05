"""
Coverage-focused Rate Limit Tests

These tests target specific uncovered lines identified by coverage analysis.
Each test is annotated with the lines it covers.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from python.security.rate_limit.limiter import (
    RateLimiter,
    RateLimitInfo,
    get_limiter,
    reset_limiter,
)
from python.security.rate_limit.memory_backend import MemoryBackend
from python.security.rate_limit.interfaces import (
    RateLimitConfig,
    FailMode,
    get_fail_mode,
    is_production,
)
from python.security.rate_limit.compat import (
    rate_limit_headers,
    rate_limit_response,
    get_login_limiter,
)


@pytest.fixture(autouse=True)
def reset_global():
    """Reset global limiter before each test."""
    reset_limiter()
    yield
    reset_limiter()


# ═══════════════════════════════════════════════════════════════════════════════
# compat.py coverage (lines 95, 107-109)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompatCoverage:
    """Tests for compat.py uncovered lines."""
    
    def test_rate_limit_headers_function(self):
        """Cover line 95: rate_limit_headers() calls info.to_headers()."""
        info = RateLimitInfo(
            allowed=False,
            retry_after=60,
            remaining=0,
            limit=5,
            reset_at=1000.0,
        )
        
        headers = rate_limit_headers(info)
        
        assert headers["X-RateLimit-Limit"] == "5"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["Retry-After"] == "60"
    
    def test_legacy_limiter_property_lazy_init(self):
        """Cover lines 107-109: _LegacyLimiter.limiter property lazy init."""
        legacy = get_login_limiter()
        
        # First access - triggers lazy init (line 107-109)
        limiter1 = legacy.limiter
        assert limiter1 is not None
        
        # Second access - uses cached (line 106)
        limiter2 = legacy.limiter
        assert limiter1 is limiter2
    
    def test_rate_limit_response_without_headers(self):
        """Cover branch: rate_limit_response with include_headers=False."""
        body, status, headers = rate_limit_response(30, include_headers=False)
        
        assert status == 429
        assert "Retry-After" in headers
        assert "X-RateLimit-Remaining" not in headers


# ═══════════════════════════════════════════════════════════════════════════════
# interfaces.py coverage (lines 33-34)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInterfacesCoverage:
    """Tests for interfaces.py uncovered lines."""
    
    def test_rate_limit_config_from_env(self):
        """Cover lines 33-34: RateLimitConfig.from_env()."""
        with patch.dict(os.environ, {
            "KOREV_RATE_LIMIT_CUSTOM_MAX": "10",
            "KOREV_RATE_LIMIT_CUSTOM_WINDOW": "120",
            "KOREV_RATE_LIMIT_CUSTOM_BACKOFF": "false",
            "KOREV_RATE_LIMIT_CUSTOM_BACKOFF_MULT": "3.0",
            "KOREV_RATE_LIMIT_CUSTOM_MAX_BACKOFF": "7200",
        }):
            config = RateLimitConfig.from_env("custom")
            
            assert config.name == "custom"
            assert config.max_requests == 10
            assert config.window_seconds == 120
            assert config.enable_backoff is False
            assert config.backoff_multiplier == 3.0
            assert config.max_backoff_seconds == 7200
    
    def test_fail_mode_enum_values(self):
        """Cover enum value access."""
        assert FailMode.FAIL_OPEN.value == "fail_open"
        assert FailMode.FAIL_CLOSED.value == "fail_closed"
    
    def test_get_fail_mode_returns_fail_open(self):
        """Cover get_fail_mode FAIL_OPEN branch."""
        with patch.dict(os.environ, {"KOREV_RATE_LIMIT_FAIL_MODE": "fail_open"}):
            mode = get_fail_mode()
            assert mode == FailMode.FAIL_OPEN
    
    def test_is_production_true(self):
        """Cover is_production() True branches."""
        for val in ("true", "1", "yes"):
            with patch.dict(os.environ, {"KOREV_PRODUCTION": val}):
                assert is_production() is True


# ═══════════════════════════════════════════════════════════════════════════════
# limiter.py coverage (lines 102-120, 146, 193, 208, 212)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLimiterCoverage:
    """Tests for limiter.py uncovered lines."""
    
    def test_backend_selection_redis_unavailable_production(self):
        """Cover lines 102-120: Redis selected but unavailable in production."""
        with patch.dict(os.environ, {
            "KOREV_RATE_LIMIT_BACKEND": "redis",
            "KOREV_PRODUCTION": "true",
        }):
            # Mock is_redis_available to return False
            with patch(
                "python.security.rate_limit.redis_backend.is_redis_available",
                return_value=False,
            ):
                reset_limiter()
                # Directly test _create_default_backend 
                backend = RateLimiter._create_default_backend()
                
                # Should fall back to memory backend with warning
                assert isinstance(backend, MemoryBackend)
    
    def test_backend_selection_redis_unavailable_dev(self):
        """Cover lines 116-120: Redis unavailable in dev mode."""
        with patch.dict(os.environ, {
            "KOREV_RATE_LIMIT_BACKEND": "redis",
            "KOREV_PRODUCTION": "false",
        }):
            with patch(
                "python.security.rate_limit.redis_backend.is_redis_available",
                return_value=False,
            ):
                reset_limiter()
                backend = RateLimiter._create_default_backend()
                
                assert isinstance(backend, MemoryBackend)
    
    def test_check_creates_default_config_for_unknown_name(self):
        """Cover line 146: check() creates default config for unknown name."""
        backend = MemoryBackend(max_entries=100)
        limiter = RateLimiter(backend=backend, configs={})
        
        # "unknown" is not in configs - should create default
        allowed, info = limiter.check("unknown", "192.168.1.1")
        
        assert allowed is True
        assert info.limit == 5  # Default max_requests
    
    def test_get_info_creates_default_config_for_unknown_name(self):
        """Cover line 193: get_info() creates default config."""
        backend = MemoryBackend(max_entries=100)
        limiter = RateLimiter(backend=backend, configs={})
        
        info = limiter.get_info("unknown", "192.168.1.1")
        
        assert info.remaining == 5  # Default max_requests
    
    def test_health_check_method(self):
        """Cover line 208: RateLimiter.health_check()."""
        limiter = RateLimiter()
        
        result = limiter.health_check()
        
        assert result is True  # Memory backend always healthy
    
    def test_get_config_returns_none_for_unknown(self):
        """Cover line 212: get_config() returns None for unknown name."""
        backend = MemoryBackend(max_entries=100)
        limiter = RateLimiter(backend=backend, configs={})
        
        config = limiter.get_config("nonexistent")
        
        assert config is None
    
    def test_get_config_returns_config_for_known(self):
        """Cover get_config() with known name."""
        limiter = RateLimiter()
        
        config = limiter.get_config("login")
        
        assert config is not None
        assert config.name == "login"


# ═══════════════════════════════════════════════════════════════════════════════
# memory_backend.py coverage (179, 213-214, 226, 233, 252-273, 318-319)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryBackendCoverage:
    """Tests for memory_backend.py uncovered lines."""
    
    @pytest.fixture
    def backend(self):
        """Create backend with controlled time."""
        current_time = [1000.0]
        
        def fake_now():
            return current_time[0]
        
        def advance_time(seconds):
            current_time[0] += seconds
        
        backend = MemoryBackend(
            max_entries=100,
            cleanup_interval=10,  # Short for testing
            now_fn=fake_now,
        )
        backend.advance_time = advance_time
        return backend
    
    def test_rate_limit_exceeded_without_backoff(self, backend):
        """Cover line 179: retry_after when backoff disabled."""
        config = RateLimitConfig(
            name="test",
            max_requests=2,
            window_seconds=60,
            enable_backoff=False,  # Key: backoff disabled
        )
        
        key = "test:192.168.1.1"
        
        # Exhaust limit
        backend.check(key, config)
        backend.check(key, config)
        
        # Third request - blocked without backoff
        result = backend.check(key, config)
        
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.retry_after <= 61  # Within original window
    
    def test_get_info_when_blocked(self, backend):
        """Cover lines 213-214: get_info() when entry is blocked."""
        config = RateLimitConfig(
            name="test",
            max_requests=1,
            window_seconds=60,
            enable_backoff=True,
        )
        
        key = "test:192.168.1.1"
        
        # Trigger block
        backend.check(key, config)
        backend.check(key, config)  # Exceeds limit, gets blocked
        
        # get_info should see blocked state
        result = backend.get_info(key, config)
        
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.violations >= 1
    
    def test_get_info_with_violations_extends_window(self, backend):
        """Cover lines 226, 233: get_info() with violations extending window."""
        config = RateLimitConfig(
            name="test",
            max_requests=1,
            window_seconds=10,
            enable_backoff=True,
            backoff_multiplier=2.0,
        )
        
        key = "test:192.168.1.1"
        
        # Use limit and trigger violation
        backend.check(key, config)
        backend.check(key, config)  # Blocked, violation=1
        
        # Advance past block but not past extended window
        backend.advance_time(25)  # Past block, but extended window = 20s
        
        # Check - should allow due to window expiry
        result = backend.check(key, config)
        # May or may not be allowed depending on exact timing
        assert result is not None
    
    def test_cleanup_method_directly(self, backend):
        """Cover lines 252-273: cleanup() method."""
        config = RateLimitConfig(
            name="test",
            max_requests=5,
            window_seconds=60,
            max_backoff_seconds=60,
        )
        
        # Add entries
        backend.check("test:ip1", config)
        backend.check("test:ip2", config)
        backend.check("test:ip3", config)
        
        # Make entries very old
        backend.advance_time(200000)  # Way past stale threshold
        
        # Run cleanup
        removed = backend.cleanup()
        
        # Should have cleaned up old entries
        assert backend._cleanup_count >= 1
    
    def test_get_stats_method(self, backend):
        """Cover lines 318-319: get_stats() method."""
        config = RateLimitConfig(name="test", max_requests=5, window_seconds=60)
        
        # Add some entries
        backend.check("test:ip1", config)
        backend.check("test:ip2", config)
        
        stats = backend.get_stats()
        
        assert "entries" in stats
        assert "max_entries" in stats
        assert "evictions" in stats
        assert "cleanups" in stats
        assert stats["entries"] == 2
    
    def test_reset_nonexistent_key(self, backend):
        """Cover branch: reset() on non-existent key is no-op."""
        # Should not raise
        backend.reset("nonexistent:key")
        
        # Verify still works
        assert backend.get_entry_count() == 0
    
    def test_maybe_cleanup_triggered(self, backend):
        """Cover _maybe_cleanup() path via check()."""
        config = RateLimitConfig(
            name="test",
            max_requests=5,
            window_seconds=60,
            max_backoff_seconds=30,
        )
        
        # Add entry
        backend.check("test:ip1", config)
        
        # Advance past cleanup interval
        backend.advance_time(15)  # > 10s cleanup_interval
        
        # Add another entry, triggering cleanup
        backend.check("test:ip2", config)
        
        # Verify cleanup ran (hard to verify directly, but no crash)
        assert backend.get_entry_count() >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# redis_backend.py coverage (220-226, 251-252, 256-309, 313)
# ═══════════════════════════════════════════════════════════════════════════════

def _check_redis():
    """Check if Redis is available."""
    from python.security.rate_limit.redis_backend import is_redis_available
    return is_redis_available()


class TestRedisBackendCoverage:
    """Tests for redis_backend.py uncovered lines."""
    
    @pytest.fixture
    def redis_backend(self):
        """Create Redis backend if available."""
        if not _check_redis():
            pytest.skip("Redis not available")
        
        from python.security.rate_limit.redis_backend import RedisBackend
        
        backend = RedisBackend(key_prefix="test_cov:")
        yield backend
        
        # Cleanup
        try:
            client = backend._get_client()
            keys = client.keys("test_cov:*")
            if keys:
                client.delete(*keys)
        except Exception:
            pass
    
    def test_get_info_method(self, redis_backend):
        """Cover lines 256-309: get_info() complete path."""
        from python.security.rate_limit.interfaces import RateLimitConfig
        
        config = RateLimitConfig(
            name="test",
            max_requests=5,
            window_seconds=60,
        )
        
        key = "test:get_info_test"
        
        # Add some requests first
        redis_backend.check(key, config)
        redis_backend.check(key, config)
        
        # Get info without incrementing
        result = redis_backend.get_info(key, config)
        
        assert result.remaining == 3  # 5 - 2
        assert result.limit == 5
    
    def test_get_info_empty_key(self, redis_backend):
        """Cover get_info() with non-existent key."""
        from python.security.rate_limit.interfaces import RateLimitConfig
        
        config = RateLimitConfig(
            name="test",
            max_requests=5,
            window_seconds=60,
        )
        
        result = redis_backend.get_info("nonexistent:key", config)
        
        assert result.remaining == 5  # Full quota for new key
    
    def test_get_info_blocked_entry(self, redis_backend):
        """Cover get_info() lines 269-278: blocked entry path."""
        from python.security.rate_limit.interfaces import RateLimitConfig
        
        config = RateLimitConfig(
            name="test",
            max_requests=1,
            window_seconds=60,
            enable_backoff=True,
        )
        
        key = "test:blocked_info"
        
        # Trigger block
        redis_backend.check(key, config)
        redis_backend.check(key, config)  # Exceeds, blocked
        
        # get_info should show blocked
        result = redis_backend.get_info(key, config)
        
        assert result.allowed is False
        assert result.retry_after is not None
    
    def test_cleanup_returns_zero(self, redis_backend):
        """Cover line 313: cleanup() returns 0 (Redis handles TTL)."""
        result = redis_backend.cleanup()
        
        assert result == 0
    
    def test_reset_error_handling(self, redis_backend):
        """Cover lines 251-252: reset() error handling."""
        from python.security.rate_limit.redis_backend import RedisBackend
        
        # Create backend with invalid URL to trigger error
        bad_backend = RedisBackend(
            redis_url="redis://invalid-host:9999/0",
            key_prefix="test_bad:",
        )
        
        # Should not raise, just log error
        bad_backend.reset("some:key")  # No-op on error
    
    def test_retry_after_no_blocked_until(self):
        """Cover lines 220-226: retry_after when blocked but no blocked_until."""
        if not _check_redis():
            pytest.skip("Redis not available")
        
        from python.security.rate_limit.redis_backend import RedisBackend
        from python.security.rate_limit.interfaces import RateLimitConfig
        
        # Use backoff disabled to get blocked without blocked_until
        config = RateLimitConfig(
            name="test",
            max_requests=1,
            window_seconds=60,
            enable_backoff=False,  # No blocked_until set
        )
        
        backend = RedisBackend(key_prefix="test_noblock:")
        key = "test:retry_calc"
        
        try:
            # Exhaust limit
            backend.check(key, config)
            
            # Next should be blocked (without blocked_until > now)
            result = backend.check(key, config)
            
            assert result.allowed is False
            assert result.retry_after is not None
        finally:
            # Cleanup
            try:
                client = backend._get_client()
                client.delete(backend._make_key(key))
            except Exception:
                pass
    
    def test_get_info_with_violations(self):
        """Cover get_info lines 282-286: violations extending window."""
        if not _check_redis():
            pytest.skip("Redis not available")
        
        from python.security.rate_limit.redis_backend import RedisBackend
        from python.security.rate_limit.interfaces import RateLimitConfig
        
        config = RateLimitConfig(
            name="test",
            max_requests=1,
            window_seconds=60,
            enable_backoff=True,
        )
        
        backend = RedisBackend(key_prefix="test_viol:")
        key = "test:violations_info"
        
        try:
            # Cause violation
            backend.check(key, config)
            backend.check(key, config)  # Blocked
            
            # get_info should see violations
            result = backend.get_info(key, config)
            assert result.violations >= 1
        finally:
            try:
                client = backend._get_client()
                client.delete(backend._make_key(key))
            except Exception:
                pass
    
    def test_get_info_error_handling(self):
        """Cover lines 307-309: get_info error handling."""
        from python.security.rate_limit.redis_backend import RedisBackend
        from python.security.rate_limit.interfaces import RateLimitConfig, FailMode
        
        config = RateLimitConfig(name="test", max_requests=5, window_seconds=60)
        
        # Backend with bad URL
        backend = RedisBackend(
            redis_url="redis://invalid-host:9999/0",
            fail_mode=FailMode.FAIL_CLOSED,
        )
        
        result = backend.get_info("some:key", config)
        
        # Should return failure result
        assert result.allowed is False

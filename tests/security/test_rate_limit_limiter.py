"""
Rate Limiter Tests

Tests verify:
1. Unified limiter API
2. Response headers generation
3. Backward-compatible API
4. Backend auto-selection
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
from python.security.rate_limit.interfaces import RateLimitConfig
from python.security.rate_limit.compat import (
    check_login_rate_limit,
    check_api_rate_limit,
    reset_login_rate_limit,
    rate_limit_response,
)


@pytest.fixture(autouse=True)
def reset_global_limiter():
    """Reset global limiter before each test."""
    reset_limiter()
    yield
    reset_limiter()


class TestRateLimitInfo:
    """Tests for RateLimitInfo."""
    
    def test_to_headers_includes_standard_headers(self):
        """to_headers() includes standard X-RateLimit-* headers."""
        info = RateLimitInfo(
            allowed=True,
            retry_after=None,
            remaining=4,
            limit=5,
            reset_at=1000.0,
        )
        
        headers = info.to_headers()
        
        assert headers["X-RateLimit-Limit"] == "5"
        assert headers["X-RateLimit-Remaining"] == "4"
        assert headers["X-RateLimit-Reset"] == "1000"
        assert "Retry-After" not in headers
    
    def test_to_headers_includes_retry_after_when_blocked(self):
        """to_headers() includes Retry-After when blocked."""
        info = RateLimitInfo(
            allowed=False,
            retry_after=60,
            remaining=0,
            limit=5,
            reset_at=1060.0,
        )
        
        headers = info.to_headers()
        
        assert headers["Retry-After"] == "60"
        assert headers["X-RateLimit-Remaining"] == "0"


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    @pytest.fixture
    def limiter(self):
        """Create a limiter with memory backend."""
        backend = MemoryBackend(max_entries=100)
        return RateLimiter(backend=backend)
    
    def test_check_returns_tuple(self, limiter):
        """check() returns (allowed, info) tuple."""
        allowed, info = limiter.check("login", "192.168.1.1")
        
        assert isinstance(allowed, bool)
        assert isinstance(info, RateLimitInfo)
    
    def test_check_uses_named_config(self, limiter):
        """check() uses configuration for named rate limit."""
        # Login has default config with 5 max requests
        for _ in range(5):
            allowed, _ = limiter.check("login", "192.168.1.1")
            assert allowed is True
        
        # 6th should be blocked
        allowed, info = limiter.check("login", "192.168.1.1")
        assert allowed is False
        assert info.retry_after is not None
    
    def test_reset_clears_rate_limit(self, limiter):
        """reset() clears rate limit for key."""
        # Use up limit
        for _ in range(5):
            limiter.check("login", "192.168.1.1")
        
        allowed, _ = limiter.check("login", "192.168.1.1")
        assert allowed is False
        
        # Reset
        limiter.reset("login", "192.168.1.1")
        
        # Should be allowed again
        allowed, _ = limiter.check("login", "192.168.1.1")
        assert allowed is True
    
    def test_get_info_does_not_increment(self, limiter):
        """get_info() returns info without incrementing counter."""
        key = "192.168.1.1"
        
        # Check once
        limiter.check("login", key)
        
        # Get info multiple times
        info1 = limiter.get_info("login", key)
        info2 = limiter.get_info("login", key)
        info3 = limiter.get_info("login", key)
        
        # Remaining should not decrease
        assert info1.remaining == info2.remaining == info3.remaining
    
    def test_different_names_have_separate_limits(self, limiter):
        """Different rate limit names are tracked separately."""
        key = "192.168.1.1"
        
        # Use up login limit
        for _ in range(5):
            limiter.check("login", key)
        
        login_allowed, _ = limiter.check("login", key)
        assert login_allowed is False
        
        # API should still be available
        api_allowed, _ = limiter.check("api", key)
        assert api_allowed is True


class TestBackwardCompatibleAPI:
    """Tests for backward-compatible functions."""
    
    def test_check_login_rate_limit_returns_tuple(self):
        """check_login_rate_limit returns (allowed, retry_after)."""
        allowed, retry_after = check_login_rate_limit("192.168.1.1")
        
        assert isinstance(allowed, bool)
        assert retry_after is None or isinstance(retry_after, int)
    
    def test_check_api_rate_limit_returns_tuple(self):
        """check_api_rate_limit returns (allowed, retry_after)."""
        allowed, retry_after = check_api_rate_limit("192.168.1.1")
        
        assert isinstance(allowed, bool)
        assert retry_after is None or isinstance(retry_after, int)
    
    def test_reset_login_rate_limit_clears_limit(self):
        """reset_login_rate_limit clears the limit."""
        ip = "192.168.1.100"
        
        # Use up limit
        for _ in range(5):
            check_login_rate_limit(ip)
        
        allowed, _ = check_login_rate_limit(ip)
        assert allowed is False
        
        # Reset
        reset_login_rate_limit(ip)
        
        # Should be allowed
        allowed, _ = check_login_rate_limit(ip)
        assert allowed is True
    
    def test_rate_limit_response_format(self):
        """rate_limit_response returns correct format."""
        body, status, headers = rate_limit_response(60)
        
        assert status == 429
        assert "60" in body
        assert headers["Retry-After"] == "60"


class TestGetLimiter:
    """Tests for global limiter singleton."""
    
    def test_get_limiter_returns_same_instance(self):
        """get_limiter() returns the same instance."""
        limiter1 = get_limiter()
        limiter2 = get_limiter()
        
        assert limiter1 is limiter2
    
    def test_reset_limiter_clears_global(self):
        """reset_limiter() clears the global instance."""
        limiter1 = get_limiter()
        reset_limiter()
        limiter2 = get_limiter()
        
        assert limiter1 is not limiter2


class TestBackendAutoSelection:
    """Tests for backend auto-selection."""
    
    def test_uses_memory_backend_in_dev(self):
        """Uses memory backend when not in production."""
        with patch.dict(os.environ, {
            "KOREV_PRODUCTION": "false",
            "KOREV_RATE_LIMIT_BACKEND": "memory",
        }):
            reset_limiter()
            limiter = get_limiter()
            
            assert isinstance(limiter.backend, MemoryBackend)
    
    def test_respects_explicit_backend_env(self):
        """Respects KOREV_RATE_LIMIT_BACKEND env var."""
        with patch.dict(os.environ, {
            "KOREV_RATE_LIMIT_BACKEND": "memory",
        }):
            reset_limiter()
            limiter = get_limiter()
            
            assert isinstance(limiter.backend, MemoryBackend)

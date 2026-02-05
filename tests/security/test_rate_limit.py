"""
Rate Limiting Tests - Backward Compatibility

These tests verify the backward-compatible API still works correctly
after the refactoring to the new pluggable backend system.
"""

import pytest

from python.security.rate_limit import (
    check_login_rate_limit,
    check_api_rate_limit,
    reset_login_rate_limit,
    rate_limit_response,
    get_login_limiter,
    get_api_limiter,
)
from python.security.rate_limit.limiter import reset_limiter


@pytest.fixture(autouse=True)
def clean_limiter():
    """Reset limiter before and after each test."""
    reset_limiter()
    yield
    reset_limiter()


class TestBackwardCompatibleAPI:
    """Tests for backward-compatible API functions."""
    
    def test_check_login_rate_limit_returns_tuple(self):
        """check_login_rate_limit returns (allowed, retry_after) tuple."""
        allowed, retry_after = check_login_rate_limit("192.168.1.1")
        
        assert isinstance(allowed, bool)
        assert allowed is True
        assert retry_after is None
    
    def test_check_login_rate_limit_blocks_after_limit(self):
        """check_login_rate_limit blocks after exceeding limit."""
        ip = "192.168.1.2"
        
        # Default limit is 5 requests per minute
        for _ in range(5):
            allowed, _ = check_login_rate_limit(ip)
            assert allowed is True
        
        # 6th request should be blocked
        allowed, retry_after = check_login_rate_limit(ip)
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_check_api_rate_limit_returns_tuple(self):
        """check_api_rate_limit returns (allowed, retry_after) tuple."""
        allowed, retry_after = check_api_rate_limit("192.168.1.3")
        
        assert isinstance(allowed, bool)
        assert allowed is True
    
    def test_reset_login_rate_limit_clears_limit(self):
        """reset_login_rate_limit clears the rate limit."""
        ip = "192.168.1.4"
        
        # Exhaust limit
        for _ in range(5):
            check_login_rate_limit(ip)
        
        allowed, _ = check_login_rate_limit(ip)
        assert allowed is False
        
        # Reset
        reset_login_rate_limit(ip)
        
        # Should be allowed again
        allowed, _ = check_login_rate_limit(ip)
        assert allowed is True
    
    def test_rate_limit_response_format(self):
        """rate_limit_response returns correct format."""
        body, status, headers = rate_limit_response(60)
        
        assert status == 429
        assert "Retry-After" in headers
        assert headers["Retry-After"] == "60"
        assert "60" in body
    
    def test_different_ips_have_separate_limits(self):
        """Different IPs have separate rate limits."""
        # Exhaust limit for IP1
        for _ in range(6):
            check_login_rate_limit("192.168.1.10")
        
        ip1_allowed, _ = check_login_rate_limit("192.168.1.10")
        assert ip1_allowed is False
        
        # IP2 should still be allowed
        ip2_allowed, _ = check_login_rate_limit("192.168.1.11")
        assert ip2_allowed is True


class TestLegacyLimiterAPI:
    """Tests for legacy limiter class compatibility."""
    
    def test_get_login_limiter_returns_object(self):
        """get_login_limiter returns a limiter-like object."""
        limiter = get_login_limiter()
        
        assert limiter is not None
        assert hasattr(limiter, 'is_allowed')
        assert hasattr(limiter, 'reset')
    
    def test_get_api_limiter_returns_object(self):
        """get_api_limiter returns a limiter-like object."""
        limiter = get_api_limiter()
        
        assert limiter is not None
        assert hasattr(limiter, 'is_allowed')
        assert hasattr(limiter, 'reset')
    
    def test_legacy_limiter_is_allowed(self):
        """Legacy limiter is_allowed method works."""
        limiter = get_login_limiter()
        
        allowed, retry_after = limiter.is_allowed("192.168.1.20")
        
        assert isinstance(allowed, bool)
        assert allowed is True
    
    def test_legacy_limiter_reset(self):
        """Legacy limiter reset method works."""
        limiter = get_login_limiter()
        ip = "192.168.1.21"
        
        # Exhaust limit
        for _ in range(6):
            limiter.is_allowed(ip)
        
        allowed, _ = limiter.is_allowed(ip)
        assert allowed is False
        
        # Reset
        limiter.reset(ip)
        
        # Should be allowed
        allowed, _ = limiter.is_allowed(ip)
        assert allowed is True


class TestRateLimitResponse:
    """Tests for rate limit response generation."""
    
    def test_response_includes_retry_after_header(self):
        """Response includes Retry-After header."""
        body, status, headers = rate_limit_response(120)
        
        assert headers["Retry-After"] == "120"
    
    def test_response_body_contains_wait_time(self):
        """Response body mentions wait time."""
        body, status, headers = rate_limit_response(30)
        
        assert "30" in body
        assert "seconds" in body.lower() or "try again" in body.lower()
    
    def test_response_status_is_429(self):
        """Response status is 429 Too Many Requests."""
        _, status, _ = rate_limit_response(60)
        
        assert status == 429

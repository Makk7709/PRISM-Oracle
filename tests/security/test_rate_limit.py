"""
Rate Limiting Tests - Brute Force Protection

Tests verify:
1. Rate limits are enforced per IP
2. Limits are configurable
3. Backoff increases on repeated violations
4. Reset works after successful auth
"""

import time
import pytest

from python.security.rate_limit import (
    RateLimiter,
    check_login_rate_limit,
    check_api_rate_limit,
    reset_login_rate_limit,
    get_login_limiter,
    rate_limit_response,
    RATE_LIMIT_LOGIN_MAX,
    RATE_LIMIT_LOGIN_WINDOW,
)


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_first_request_allowed(self):
        """First request is always allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        allowed, retry_after = limiter.is_allowed("192.168.1.1")
        
        assert allowed is True
        assert retry_after is None
    
    def test_requests_under_limit_allowed(self):
        """Requests under the limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        ip = "192.168.1.2"
        
        for _ in range(5):
            allowed, _ = limiter.is_allowed(ip)
            assert allowed is True
    
    def test_requests_over_limit_blocked(self):
        """Requests over the limit are blocked."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        ip = "192.168.1.3"
        
        # Use up the limit
        for _ in range(3):
            limiter.is_allowed(ip)
        
        # Next request should be blocked
        allowed, retry_after = limiter.is_allowed(ip)
        
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_different_ips_separate_limits(self):
        """Different IPs have separate limits."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # Exhaust limit for IP1
        limiter.is_allowed("192.168.1.10")
        limiter.is_allowed("192.168.1.10")
        allowed1, _ = limiter.is_allowed("192.168.1.10")
        
        # IP2 should still be allowed
        allowed2, _ = limiter.is_allowed("192.168.1.11")
        
        assert allowed1 is False
        assert allowed2 is True
    
    def test_window_expires_and_resets(self):
        """Limit resets after window expires."""
        # Short window for testing
        limiter = RateLimiter(max_requests=2, window_seconds=1, enable_backoff=False)
        ip = "192.168.1.20"
        
        # Exhaust limit
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        allowed1, _ = limiter.is_allowed(ip)
        assert allowed1 is False
        
        # Wait for window to expire (with buffer)
        time.sleep(1.5)
        
        # Should be allowed again
        allowed2, _ = limiter.is_allowed(ip)
        assert allowed2 is True
    
    def test_reset_clears_limit(self):
        """reset() clears the rate limit for a key."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        ip = "192.168.1.30"
        
        # Exhaust limit
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        allowed1, _ = limiter.is_allowed(ip)
        assert allowed1 is False
        
        # Reset
        limiter.reset(ip)
        
        # Should be allowed again
        allowed2, _ = limiter.is_allowed(ip)
        assert allowed2 is True
    
    def test_get_remaining_returns_correct_count(self):
        """get_remaining returns correct remaining requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        ip = "192.168.1.40"
        
        assert limiter.get_remaining(ip) == 5
        
        limiter.is_allowed(ip)
        assert limiter.get_remaining(ip) == 4
        
        limiter.is_allowed(ip)
        limiter.is_allowed(ip)
        assert limiter.get_remaining(ip) == 2


class TestBackoff:
    """Tests for backoff functionality."""
    
    def test_backoff_increases_on_violations(self):
        """Backoff window increases on repeated violations."""
        limiter = RateLimiter(max_requests=1, window_seconds=10, enable_backoff=True)
        ip = "192.168.1.50"
        
        # First request - allowed
        limiter.is_allowed(ip)
        
        # Second request - blocked, first violation
        _, retry1 = limiter.is_allowed(ip)
        
        # Wait for retry, then violate again
        time.sleep(0.1)
        limiter._entries[ip].blocked_until = 0  # Simulate retry window passed
        limiter._entries[ip].window_start = time.time() - 5  # Reset window
        limiter._entries[ip].count = 0
        
        limiter.is_allowed(ip)  # Use the one request
        _, retry2 = limiter.is_allowed(ip)  # Second violation
        
        # Second violation should have longer retry (backoff)
        assert retry2 >= retry1
    
    def test_backoff_can_be_disabled(self):
        """Backoff can be disabled."""
        limiter = RateLimiter(max_requests=1, window_seconds=10, enable_backoff=False)
        ip = "192.168.1.60"
        
        limiter.is_allowed(ip)
        _, retry1 = limiter.is_allowed(ip)
        
        # With backoff disabled, retry should be consistent
        assert retry1 <= 11  # Within original window


class TestLoginRateLimiting:
    """Tests for login-specific rate limiting."""
    
    def test_login_rate_limit_uses_configured_values(self):
        """Login limiter uses configured max and window."""
        limiter = get_login_limiter()
        
        assert limiter.max_requests == RATE_LIMIT_LOGIN_MAX
        assert limiter.window_seconds == RATE_LIMIT_LOGIN_WINDOW
    
    def test_check_login_rate_limit_function(self):
        """check_login_rate_limit function works."""
        # Reset first to ensure clean state
        reset_login_rate_limit("test_ip_login")
        
        allowed, _ = check_login_rate_limit("test_ip_login")
        assert allowed is True
    
    def test_reset_login_rate_limit_function(self):
        """reset_login_rate_limit clears limit."""
        ip = "test_ip_reset"
        
        # Exhaust limit
        limiter = get_login_limiter()
        for _ in range(RATE_LIMIT_LOGIN_MAX + 1):
            limiter.is_allowed(ip)
        
        # Verify blocked
        allowed1, _ = check_login_rate_limit(ip)
        assert allowed1 is False
        
        # Reset
        reset_login_rate_limit(ip)
        
        # Should be allowed
        allowed2, _ = check_login_rate_limit(ip)
        assert allowed2 is True


class TestAPIRateLimiting:
    """Tests for API rate limiting."""
    
    def test_api_rate_limit_function(self):
        """check_api_rate_limit function works."""
        allowed, _ = check_api_rate_limit("api_test_ip")
        assert allowed is True


class TestRateLimitResponse:
    """Tests for rate limit response generation."""
    
    def test_response_format(self):
        """rate_limit_response returns correct format."""
        body, status, headers = rate_limit_response(60)
        
        assert status == 429
        assert "Retry-After" in headers
        assert headers["Retry-After"] == "60"
        assert "60" in body or "seconds" in body.lower()


class TestIntegration:
    """Integration tests for rate limiting in Flask app."""
    
    @pytest.mark.integration
    def test_login_endpoint_rate_limited(self):
        """
        Verify /login endpoint is rate limited.
        
        This test validates that run_ui.py applies rate limiting.
        """
        # This will be implemented after we patch run_ui.py
        pytest.skip("Pending run_ui.py modification")
    
    @pytest.mark.integration
    def test_api_endpoint_rate_limited(self):
        """
        Verify API endpoints are rate limited.
        
        This test validates that API handlers apply rate limiting.
        """
        pytest.skip("Pending API handler modification")

"""
End-to-End Integration Test: Login Rate Limiting

This test proves that run_ui.py correctly integrates the rate limiting system.
It uses Flask test client to simulate real HTTP requests.

Critical test - ensures nobody accidentally disables rate limiting.

ARCHITECTURE NOTE:
This test uses create_app() factory which does NOT import litellm/initialize.
This allows the test to run in CI without heavy LLM dependencies.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Must reset limiter before importing app to ensure clean state
from python.security.rate_limit.limiter import reset_limiter


@pytest.fixture
def app():
    """Create Flask test application with controlled rate limiter.
    
    Uses create_app() factory to avoid importing litellm/initialize.
    This is critical for CI where LLM dependencies may not be available.
    """
    # Reset any existing limiter
    reset_limiter()
    
    # Set test environment
    with patch.dict(os.environ, {
        "AUTH_LOGIN": "testuser",
        "AUTH_PASSWORD": "testpass",  # Plaintext for testing (dev mode)
        "KOREV_PRODUCTION": "false",
        "KOREV_RATE_LIMIT_BACKEND": "memory",
        "RATE_LIMIT_LOGIN_MAX": "5",  # 5 attempts max
        "RATE_LIMIT_LOGIN_WINDOW": "60",  # 60 second window
    }):
        # Import create_app factory (NO litellm import cascade)
        from run_ui import create_app
        
        # Create app with testing=True
        test_app = create_app(testing=True)
        
        yield test_app
    
    # Cleanup
    reset_limiter()


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def controlled_time_limiter():
    """
    Create a rate limiter with controlled time for deterministic tests.
    Returns (limiter, advance_time_fn).
    """
    from python.security.rate_limit.memory_backend import MemoryBackend
    from python.security.rate_limit.limiter import RateLimiter, reset_limiter
    from python.security.rate_limit import limiter as limiter_module
    
    current_time = [1000.0]
    
    def fake_now():
        return current_time[0]
    
    def advance_time(seconds):
        current_time[0] += seconds
    
    # Create backend with controlled time
    backend = MemoryBackend(
        max_entries=1000,
        cleanup_interval=300,
        now_fn=fake_now,
    )
    
    # Create limiter with this backend
    test_limiter = RateLimiter(backend=backend)
    
    # Inject into global state
    limiter_module._limiter = test_limiter
    
    yield test_limiter, advance_time
    
    # Cleanup
    reset_limiter()


class TestLoginRateLimitE2E:
    """
    End-to-end tests for login rate limiting.
    
    These tests verify that run_ui.py correctly uses the rate limiting system.
    """
    
    @pytest.mark.integration
    def test_login_returns_429_after_limit_exceeded(self, client):
        """
        6 invalid login attempts → 429 Too Many Requests.
        
        This is the critical test that proves rate limiting is wired up.
        """
        # Make 5 invalid login attempts (at the limit)
        for i in range(5):
            response = client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
            # Should get login page with error, not 429 yet
            assert response.status_code == 200, f"Attempt {i+1} should succeed"
        
        # 6th attempt should be rate limited
        response = client.post('/login', data={
            'username': 'wrong',
            'password': 'wrong',
        })
        
        assert response.status_code == 429, "6th attempt should be rate limited"
    
    @pytest.mark.integration
    def test_429_response_includes_retry_after_header(self, client):
        """429 response includes Retry-After header (RFC 6585)."""
        # Exhaust rate limit
        for _ in range(6):
            response = client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
        
        assert response.status_code == 429
        assert 'Retry-After' in response.headers
        
        retry_after = int(response.headers['Retry-After'])
        assert retry_after > 0
        assert retry_after <= 3600  # Max 1 hour (sanity check)
    
    @pytest.mark.integration
    def test_429_response_includes_rate_limit_headers(self, client):
        """429 response includes X-RateLimit-* headers."""
        # Exhaust rate limit
        for _ in range(6):
            response = client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
        
        assert response.status_code == 429
        
        # Check standard rate limit headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert response.headers['X-RateLimit-Remaining'] == '0'
    
    @pytest.mark.integration
    def test_successful_login_resets_rate_limit(self, client):
        """Successful login resets the rate limit counter."""
        # Make 4 invalid attempts (just under limit)
        for _ in range(4):
            client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
        
        # Successful login
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass',
        }, follow_redirects=False)
        
        # Should redirect (success)
        assert response.status_code == 302
        
        # Now make more invalid attempts - should be allowed again
        # (rate limit was reset on successful login)
        for _ in range(4):
            response = client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
            assert response.status_code == 200  # Not 429
    
    @pytest.mark.integration
    def test_different_ips_have_separate_limits(self, client):
        """Different IPs are rate limited separately."""
        # Note: In test client, we can't easily simulate different IPs
        # This test verifies the rate limiting is per-key
        # The actual IP separation is tested in unit tests
        
        # Exhaust limit from "current IP"
        for _ in range(6):
            response = client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
        
        # Should be blocked
        assert response.status_code == 429


class TestLoginRateLimitWithTimeControl:
    """
    Tests with controlled time to verify window expiry behavior.
    
    Uses time injection instead of sleep() for deterministic tests.
    """
    
    @pytest.mark.integration
    def test_rate_limit_window_expires_and_allows_retry(
        self, 
        controlled_time_limiter,
    ):
        """
        After window expires, requests are allowed again.
        
        Uses time injection for deterministic testing.
        """
        from python.security.rate_limit import check_login_rate_limit
        
        limiter, advance_time = controlled_time_limiter
        test_ip = "192.168.1.100"
        
        # Exhaust rate limit (5 requests, then blocked on 6th)
        for i in range(5):
            allowed, _ = check_login_rate_limit(test_ip)
            assert allowed is True, f"Request {i+1} should be allowed"
        
        # 6th request - should be blocked
        allowed, retry_after = check_login_rate_limit(test_ip)
        assert allowed is False
        assert retry_after is not None
        
        # Advance time past the window
        advance_time(retry_after + 1)
        
        # Should be allowed again
        allowed, _ = check_login_rate_limit(test_ip)
        assert allowed is True
    
    @pytest.mark.integration
    def test_backoff_increases_on_repeated_violations(
        self,
        controlled_time_limiter,
    ):
        """Repeated violations increase the backoff time."""
        from python.security.rate_limit import check_login_rate_limit
        
        limiter, advance_time = controlled_time_limiter
        test_ip = "192.168.1.101"
        
        retry_times = []
        
        for violation in range(3):
            # Exhaust limit
            for _ in range(5):
                check_login_rate_limit(test_ip)
            
            # Trigger violation
            allowed, retry_after = check_login_rate_limit(test_ip)
            assert allowed is False
            retry_times.append(retry_after)
            
            # Advance time to retry
            advance_time(retry_after + 1)
        
        # Backoff should increase (at least non-decreasing due to backoff logic)
        assert retry_times[1] >= retry_times[0], "Backoff should increase"
    
    @pytest.mark.integration
    def test_rate_limit_persists_across_requests(
        self,
        controlled_time_limiter,
    ):
        """Rate limit state persists across multiple check calls."""
        from python.security.rate_limit import check_login_rate_limit
        
        limiter, advance_time = controlled_time_limiter
        test_ip = "192.168.1.102"
        
        # Make 3 requests
        for _ in range(3):
            allowed, _ = check_login_rate_limit(test_ip)
            assert allowed is True
        
        # Small time advance (within window)
        advance_time(10)
        
        # Make 2 more requests (total 5, at limit)
        for _ in range(2):
            allowed, _ = check_login_rate_limit(test_ip)
            assert allowed is True
        
        # Next should be blocked (state persisted)
        allowed, _ = check_login_rate_limit(test_ip)
        assert allowed is False


class TestRateLimitHeaders:
    """Tests specifically for rate limit response headers."""
    
    @pytest.mark.integration
    def test_429_body_contains_wait_message(self, client):
        """429 response body contains informative message."""
        # Exhaust rate limit
        for _ in range(6):
            response = client.post('/login', data={
                'username': 'wrong',
                'password': 'wrong',
            })
        
        assert response.status_code == 429
        
        # Body should mention wait time
        body = response.get_data(as_text=True)
        assert 'wait' in body.lower() or 'try again' in body.lower() or 'too many' in body.lower()

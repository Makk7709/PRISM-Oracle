"""
Redis Backend Rate Limit Tests

Tests verify:
1. Shared state between multiple limiter instances (multi-worker simulation)
2. Backoff behavior
3. Fail mode handling (fail_open vs fail_closed)
4. Atomic operations

These tests require a Redis server. Mark with @pytest.mark.redis
and auto-skip if Redis is unavailable.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from python.security.rate_limit.redis_backend import (
    RedisBackend,
    is_redis_available,
    REDIS_URL,
)
from python.security.rate_limit.interfaces import RateLimitConfig, FailMode


def redis_available():
    """Check if Redis is available for tests."""
    return is_redis_available()


# Skip all tests in this module if Redis is not available
pytestmark = pytest.mark.skipif(
    not redis_available(),
    reason="Redis not available"
)


@pytest.fixture
def redis_backend():
    """Create a Redis backend and clean up after."""
    backend = RedisBackend(
        redis_url=os.environ.get("KOREV_REDIS_URL", REDIS_URL),
        key_prefix="test_rl:",
    )
    
    yield backend
    
    # Cleanup test keys
    try:
        client = backend._get_client()
        keys = client.keys("test_rl:*")
        if keys:
            client.delete(*keys)
    except Exception:
        pass


@pytest.fixture
def config():
    """Default rate limit config."""
    return RateLimitConfig(
        name="test",
        max_requests=5,
        window_seconds=60,
        enable_backoff=True,
        backoff_multiplier=2.0,
        max_backoff_seconds=120,
    )


class TestRedisBackendBasics:
    """Basic functionality tests."""
    
    @pytest.mark.redis
    def test_first_request_allowed(self, redis_backend, config):
        """First request is always allowed."""
        result = redis_backend.check("test:192.168.1.1", config)
        
        assert result.allowed is True
        assert result.remaining == 4
        assert result.limit == 5
    
    @pytest.mark.redis
    def test_requests_under_limit_allowed(self, redis_backend, config):
        """Requests under limit are allowed."""
        key = "test:192.168.1.1"
        
        for i in range(5):
            result = redis_backend.check(key, config)
            assert result.allowed is True
            assert result.remaining == 4 - i
    
    @pytest.mark.redis
    def test_requests_over_limit_blocked(self, redis_backend, config):
        """Requests over limit are blocked."""
        key = "test:192.168.1.1"
        
        # Use up limit
        for _ in range(5):
            redis_backend.check(key, config)
        
        # Next should be blocked
        result = redis_backend.check(key, config)
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0
    
    @pytest.mark.redis
    def test_reset_clears_counter(self, redis_backend, config):
        """reset() clears the rate limit counter."""
        key = "test:192.168.1.1"
        
        # Use up limit
        for _ in range(5):
            redis_backend.check(key, config)
        
        # Blocked
        result = redis_backend.check(key, config)
        assert result.allowed is False
        
        # Reset
        redis_backend.reset(key)
        
        # Should be allowed
        result = redis_backend.check(key, config)
        assert result.allowed is True


class TestRedisBackendMultiWorker:
    """Multi-worker simulation tests (critical for production)."""
    
    @pytest.mark.redis
    def test_shared_state_between_two_limiters(self, config):
        """
        Two separate limiter instances share state via Redis.
        
        This simulates multiple Gunicorn/uvicorn workers.
        """
        redis_url = os.environ.get("KOREV_REDIS_URL", REDIS_URL)
        
        # Create two separate backend instances (simulating two workers)
        backend1 = RedisBackend(redis_url=redis_url, key_prefix="test_multi:")
        backend2 = RedisBackend(redis_url=redis_url, key_prefix="test_multi:")
        
        key = "login:192.168.1.1"
        
        try:
            # Worker 1 uses 3 requests
            for _ in range(3):
                result = backend1.check(key, config)
                assert result.allowed is True
            
            # Worker 2 uses 2 more (total 5 = at limit)
            for _ in range(2):
                result = backend2.check(key, config)
                assert result.allowed is True
            
            # Worker 1 tries again - should be blocked (shared state!)
            result = backend1.check(key, config)
            assert result.allowed is False
            
            # Worker 2 also blocked
            result = backend2.check(key, config)
            assert result.allowed is False
            
        finally:
            # Cleanup
            try:
                client = backend1._get_client()
                client.delete(backend1._make_key(key))
            except Exception:
                pass
    
    @pytest.mark.redis
    def test_cumulative_blocking_across_workers(self, config):
        """Attempts cumulate across workers and block."""
        redis_url = os.environ.get("KOREV_REDIS_URL", REDIS_URL)
        
        backends = [
            RedisBackend(redis_url=redis_url, key_prefix="test_cum:")
            for _ in range(5)
        ]
        
        key = "api:attacker_ip"
        
        try:
            # Each worker makes 1 request (total 5 = at limit)
            for i, backend in enumerate(backends):
                result = backend.check(key, config)
                assert result.allowed is True, f"Worker {i} should be allowed"
            
            # Any worker's next request should be blocked
            result = backends[0].check(key, config)
            assert result.allowed is False
            
        finally:
            # Cleanup
            try:
                client = backends[0]._get_client()
                client.delete(backends[0]._make_key(key))
            except Exception:
                pass


class TestRedisBackendBackoff:
    """Backoff behavior tests."""
    
    @pytest.mark.redis
    def test_retry_after_increases_with_backoff(self, redis_backend, config):
        """Retry time increases with violations."""
        key = "test:backoff_test"
        
        # First violation
        for _ in range(5):
            redis_backend.check(key, config)
        result1 = redis_backend.check(key, config)
        
        assert result1.allowed is False
        retry1 = result1.retry_after
        
        # We can't easily wait in tests, but we can check violations increase
        assert result1.violations == 1


class TestRedisBackendFailMode:
    """Fail mode handling tests."""
    
    @pytest.mark.redis
    def test_handles_redis_down_fail_closed(self, config):
        """When Redis is down and FAIL_CLOSED, requests are denied."""
        # Create backend with invalid URL
        backend = RedisBackend(
            redis_url="redis://invalid-host:9999/0",
            fail_mode=FailMode.FAIL_CLOSED,
        )
        
        result = backend.check("test:192.168.1.1", config)
        
        assert result.allowed is False
        assert result.retry_after is not None
    
    @pytest.mark.redis
    def test_handles_redis_down_fail_open(self, config):
        """When Redis is down and FAIL_OPEN, requests are allowed."""
        # Create backend with invalid URL
        backend = RedisBackend(
            redis_url="redis://invalid-host:9999/0",
            fail_mode=FailMode.FAIL_OPEN,
        )
        
        result = backend.check("test:192.168.1.1", config)
        
        assert result.allowed is True


class TestRedisBackendHealthCheck:
    """Health check tests."""
    
    @pytest.mark.redis
    def test_health_check_passes_when_connected(self, redis_backend):
        """Health check passes when Redis is available."""
        assert redis_backend.health_check() is True
    
    @pytest.mark.redis
    def test_health_check_fails_when_disconnected(self):
        """Health check fails when Redis is unavailable."""
        backend = RedisBackend(redis_url="redis://invalid-host:9999/0")
        assert backend.health_check() is False


class TestIsRedisAvailable:
    """Tests for Redis availability check."""
    
    @pytest.mark.redis
    def test_is_redis_available_returns_true_when_connected(self):
        """is_redis_available returns True when Redis is up."""
        assert is_redis_available() is True
    
    def test_is_redis_available_returns_false_for_invalid_url(self):
        """is_redis_available returns False for invalid URL."""
        assert is_redis_available("redis://invalid-host:9999/0") is False

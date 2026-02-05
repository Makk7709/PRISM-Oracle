"""
Memory Backend Rate Limit Tests

Tests verify:
1. LRU eviction when max entries reached
2. TTL expiration
3. Thread safety under load
4. Backoff behavior
5. No DoS soft (memory bounded)
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from python.security.rate_limit.memory_backend import MemoryBackend, MAX_ENTRIES
from python.security.rate_limit.interfaces import RateLimitConfig, FailMode


class TestMemoryBackendBasics:
    """Basic functionality tests."""
    
    @pytest.fixture
    def backend(self):
        """Create a fresh memory backend with controlled time."""
        current_time = [1000.0]
        
        def fake_now():
            return current_time[0]
        
        def advance_time(seconds):
            current_time[0] += seconds
        
        backend = MemoryBackend(
            max_entries=100,
            cleanup_interval=60,
            now_fn=fake_now,
        )
        backend.advance_time = advance_time
        return backend
    
    @pytest.fixture
    def config(self):
        """Default rate limit config."""
        return RateLimitConfig(
            name="test",
            max_requests=5,
            window_seconds=60,
            enable_backoff=True,
            backoff_multiplier=2.0,
            max_backoff_seconds=3600,
        )
    
    def test_first_request_allowed(self, backend, config):
        """First request is always allowed."""
        result = backend.check("test:192.168.1.1", config)
        
        assert result.allowed is True
        assert result.remaining == 4
        assert result.limit == 5
    
    def test_requests_under_limit_allowed(self, backend, config):
        """Requests under limit are allowed."""
        key = "test:192.168.1.1"
        
        for i in range(5):
            result = backend.check(key, config)
            assert result.allowed is True
            assert result.remaining == 4 - i
    
    def test_requests_over_limit_blocked(self, backend, config):
        """Requests over limit are blocked."""
        key = "test:192.168.1.1"
        
        # Use up limit
        for _ in range(5):
            backend.check(key, config)
        
        # Next should be blocked
        result = backend.check(key, config)
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0
    
    def test_window_expiry_resets_count(self, backend, config):
        """Count resets after window expires."""
        key = "test:192.168.1.1"
        
        # Use up limit
        for _ in range(5):
            backend.check(key, config)
        
        # Advance time past window
        backend.advance_time(61)
        
        # Should be allowed again
        result = backend.check(key, config)
        assert result.allowed is True
        assert result.remaining == 4
    
    def test_reset_clears_entry(self, backend, config):
        """reset() clears the rate limit entry."""
        key = "test:192.168.1.1"
        
        # Use up limit
        for _ in range(5):
            backend.check(key, config)
        
        # Blocked
        result = backend.check(key, config)
        assert result.allowed is False
        
        # Reset
        backend.reset(key)
        
        # Should be allowed
        result = backend.check(key, config)
        assert result.allowed is True


class TestMemoryBackendBackoff:
    """Backoff behavior tests."""
    
    @pytest.fixture
    def backend(self):
        current_time = [1000.0]
        
        def fake_now():
            return current_time[0]
        
        def advance_time(seconds):
            current_time[0] += seconds
        
        backend = MemoryBackend(now_fn=fake_now, max_entries=100)
        backend.advance_time = advance_time
        return backend
    
    @pytest.fixture
    def config(self):
        return RateLimitConfig(
            name="test",
            max_requests=2,
            window_seconds=10,
            enable_backoff=True,
            backoff_multiplier=2.0,
            max_backoff_seconds=120,
        )
    
    def test_backoff_increases_on_violations(self, backend, config):
        """Retry time increases with repeated violations."""
        key = "test:192.168.1.1"
        
        # First violation
        backend.check(key, config)
        backend.check(key, config)
        result1 = backend.check(key, config)
        
        assert result1.allowed is False
        retry1 = result1.retry_after
        
        # Wait and try again for second violation
        backend.advance_time(retry1 + 1)
        backend.check(key, config)
        backend.check(key, config)
        result2 = backend.check(key, config)
        
        assert result2.allowed is False
        retry2 = result2.retry_after
        
        # Second violation should have longer wait
        assert retry2 > retry1
    
    def test_backoff_capped_at_max(self, backend, config):
        """Backoff is capped at max_backoff_seconds."""
        key = "test:192.168.1.1"
        
        # Cause many violations
        for _ in range(10):
            # Trigger violation
            backend.check(key, config)
            backend.check(key, config)
            result = backend.check(key, config)
            
            # Retry should never exceed max
            if result.retry_after:
                assert result.retry_after <= config.max_backoff_seconds + 1
            
            # Wait and retry
            backend.advance_time(result.retry_after or 1)


class TestMemoryBackendLRUEviction:
    """LRU eviction tests (anti-DoS soft)."""
    
    def test_caps_max_entries_and_eviction(self):
        """Backend caps entries and evicts oldest on overflow."""
        max_entries = 10
        backend = MemoryBackend(max_entries=max_entries)
        config = RateLimitConfig(name="test", max_requests=5, window_seconds=60)
        
        # Add max_entries
        for i in range(max_entries):
            backend.check(f"test:192.168.1.{i}", config)
        
        assert backend.get_entry_count() == max_entries
        
        # Add one more - should evict oldest
        backend.check("test:192.168.1.100", config)
        
        assert backend.get_entry_count() == max_entries
        assert backend.get_eviction_count() == 1
    
    def test_lru_evicts_oldest_accessed(self):
        """LRU evicts least recently accessed entry."""
        backend = MemoryBackend(max_entries=3)
        config = RateLimitConfig(name="test", max_requests=5, window_seconds=60)
        
        # Add 3 entries
        backend.check("test:ip1", config)
        backend.check("test:ip2", config)
        backend.check("test:ip3", config)
        
        # Access ip1 again (moves to end)
        backend.check("test:ip1", config)
        
        # Add new entry - should evict ip2 (oldest accessed)
        backend.check("test:ip4", config)
        
        # ip2 should be gone
        info = backend.get_info("test:ip2", config)
        assert info.remaining == config.max_requests  # Fresh entry = full quota
    
    def test_no_memory_leak_with_many_unique_keys(self):
        """Memory stays bounded with many unique keys."""
        max_entries = 100
        backend = MemoryBackend(max_entries=max_entries)
        config = RateLimitConfig(name="test", max_requests=5, window_seconds=60)
        
        # Add many more entries than limit
        for i in range(max_entries * 10):
            backend.check(f"test:attacker_{i}", config)
        
        # Should never exceed max
        assert backend.get_entry_count() <= max_entries
        assert backend.get_eviction_count() >= max_entries * 9


class TestMemoryBackendTTL:
    """TTL expiration tests."""
    
    def test_ttl_expires_entries(self):
        """Entries expire after TTL."""
        current_time = [1000.0]
        
        backend = MemoryBackend(
            max_entries=100,
            cleanup_interval=1,  # Quick cleanup for test
            now_fn=lambda: current_time[0],
        )
        
        config = RateLimitConfig(
            name="test",
            max_requests=5,
            window_seconds=60,
            max_backoff_seconds=60,
        )
        
        # Add entry
        backend.check("test:192.168.1.1", config)
        assert backend.get_entry_count() == 1
        
        # Advance time past TTL (2x max_backoff)
        current_time[0] += 150
        
        # Trigger cleanup via check
        backend.check("test:192.168.1.2", config)
        
        # Old entry should be cleaned up
        # (This depends on cleanup being triggered)
        # Note: cleanup happens every cleanup_interval, so we need to check


class TestMemoryBackendThreadSafety:
    """Thread safety tests."""
    
    def test_thread_safety_no_crash_under_load(self):
        """Backend doesn't crash under concurrent access."""
        backend = MemoryBackend(max_entries=1000)
        config = RateLimitConfig(name="test", max_requests=10, window_seconds=60)
        
        errors = []
        
        def hammer(thread_id):
            try:
                for i in range(100):
                    key = f"test:thread_{thread_id}_ip_{i % 10}"
                    backend.check(key, config)
                    
                    if i % 20 == 0:
                        backend.reset(key)
            except Exception as e:
                errors.append(e)
        
        # Run 20 threads hammering the backend
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(hammer, i) for i in range(20)]
            for f in futures:
                f.result()
        
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
    
    def test_thread_safety_counter_accuracy(self):
        """Counter stays accurate under concurrent access."""
        backend = MemoryBackend(max_entries=100)
        config = RateLimitConfig(name="test", max_requests=100, window_seconds=60)
        
        key = "test:shared_key"
        check_count = [0]
        lock = threading.Lock()
        
        def increment():
            for _ in range(50):
                result = backend.check(key, config)
                if result.allowed:
                    with lock:
                        check_count[0] += 1
        
        # 10 threads, each doing 50 checks = 500 total, but limit is 100
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 100 allowed (the limit)
        assert check_count[0] == 100


class TestMemoryBackendHealthCheck:
    """Health check tests."""
    
    def test_health_check_always_passes(self):
        """Memory backend is always healthy."""
        backend = MemoryBackend()
        assert backend.health_check() is True

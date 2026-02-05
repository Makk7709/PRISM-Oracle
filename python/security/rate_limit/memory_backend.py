"""
In-Memory Rate Limit Backend

Features:
- LRU eviction when max entries reached
- TTL-based expiration
- Thread-safe with fine-grained locking
- Suitable for single-process deployments (dev mode)

Limitations:
- Not shared between workers/processes
- State lost on restart
"""

import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable

from python.security.rate_limit.interfaces import (
    RateLimitBackend,
    RateLimitConfig,
    RateLimitResult,
    FailMode,
)


# Configuration
MAX_ENTRIES = int(os.environ.get("KOREV_RATE_LIMIT_MAX_ENTRIES", "50000"))
CLEANUP_INTERVAL = int(os.environ.get("KOREV_RATE_LIMIT_CLEANUP_INTERVAL", "300"))  # 5 min


@dataclass
class MemoryEntry:
    """Rate limit entry stored in memory."""
    count: int = 0
    window_start: float = 0.0
    violations: int = 0
    blocked_until: float = 0.0
    last_access: float = 0.0


class MemoryBackend(RateLimitBackend):
    """
    In-memory rate limit backend with LRU eviction and TTL.
    
    Thread-safe implementation suitable for single-process deployments.
    For multi-process/distributed, use RedisBackend.
    """
    
    def __init__(
        self,
        max_entries: int = MAX_ENTRIES,
        cleanup_interval: float = CLEANUP_INTERVAL,
        fail_mode: FailMode = FailMode.FAIL_CLOSED,
        now_fn: Optional[Callable[[], float]] = None,
    ):
        """
        Initialize memory backend.
        
        Args:
            max_entries: Maximum entries before LRU eviction
            cleanup_interval: Seconds between TTL cleanup runs
            fail_mode: Behavior on failure (always healthy for memory)
            now_fn: Time provider for testing
        """
        super().__init__(fail_mode=fail_mode, now_fn=now_fn)
        
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        
        # OrderedDict for LRU behavior
        self._entries: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._lock = threading.RLock()  # Reentrant for nested calls
        self._last_cleanup = 0.0
        
        # Stats for monitoring
        self._eviction_count = 0
        self._cleanup_count = 0
    
    def check(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> RateLimitResult:
        """Check if request is allowed and increment counter."""
        now = self.now()
        
        with self._lock:
            # Periodic cleanup
            self._maybe_cleanup(now, config)
            
            # Get or create entry
            if key not in self._entries:
                # Check if we need to evict before adding
                self._ensure_capacity()
                
                entry = MemoryEntry(
                    count=1,
                    window_start=now,
                    last_access=now,
                )
                self._entries[key] = entry
                
                return RateLimitResult(
                    allowed=True,
                    remaining=config.max_requests - 1,
                    limit=config.max_requests,
                    reset_at=now + config.window_seconds,
                    violations=0,
                )
            
            entry = self._entries[key]
            entry.last_access = now
            
            # Move to end for LRU
            self._entries.move_to_end(key)
            
            # Check if blocked due to backoff
            if entry.blocked_until > now:
                retry_after = int(entry.blocked_until - now) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=config.max_requests,
                    reset_at=entry.blocked_until,
                    retry_after=retry_after,
                    violations=entry.violations,
                )
            
            # Calculate effective window (backoff extends window)
            effective_window = config.window_seconds
            if config.enable_backoff and entry.violations > 0:
                effective_window = min(
                    config.window_seconds * (config.backoff_multiplier ** entry.violations),
                    config.max_backoff_seconds,
                )
            
            # Check if window expired - reset
            if now - entry.window_start >= effective_window:
                entry.count = 1
                entry.window_start = now
                # Don't reset violations - they persist across windows
                
                return RateLimitResult(
                    allowed=True,
                    remaining=config.max_requests - 1,
                    limit=config.max_requests,
                    reset_at=now + config.window_seconds,
                    violations=entry.violations,
                )
            
            # Check if under limit
            if entry.count < config.max_requests:
                entry.count += 1
                remaining = config.max_requests - entry.count
                reset_at = entry.window_start + effective_window
                
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    limit=config.max_requests,
                    reset_at=reset_at,
                    violations=entry.violations,
                )
            
            # Rate limit exceeded - apply backoff
            entry.violations += 1
            
            if config.enable_backoff:
                block_duration = min(
                    effective_window * config.backoff_multiplier,
                    config.max_backoff_seconds,
                )
                entry.blocked_until = now + block_duration
                retry_after = int(block_duration) + 1
            else:
                retry_after = int(effective_window - (now - entry.window_start)) + 1
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=config.max_requests,
                reset_at=entry.blocked_until if config.enable_backoff else entry.window_start + effective_window,
                retry_after=retry_after,
                violations=entry.violations,
            )
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
    
    def get_info(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Get current rate limit info without incrementing."""
        now = self.now()
        
        with self._lock:
            if key not in self._entries:
                return RateLimitResult(
                    allowed=True,
                    remaining=config.max_requests,
                    limit=config.max_requests,
                    reset_at=now + config.window_seconds,
                )
            
            entry = self._entries[key]
            
            # Check if blocked
            if entry.blocked_until > now:
                retry_after = int(entry.blocked_until - now) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=config.max_requests,
                    reset_at=entry.blocked_until,
                    retry_after=retry_after,
                    violations=entry.violations,
                )
            
            # Calculate effective window
            effective_window = config.window_seconds
            if config.enable_backoff and entry.violations > 0:
                effective_window = min(
                    config.window_seconds * (config.backoff_multiplier ** entry.violations),
                    config.max_backoff_seconds,
                )
            
            # Check if window expired
            if now - entry.window_start >= effective_window:
                return RateLimitResult(
                    allowed=True,
                    remaining=config.max_requests,
                    limit=config.max_requests,
                    reset_at=now + config.window_seconds,
                    violations=entry.violations,
                )
            
            remaining = max(0, config.max_requests - entry.count)
            return RateLimitResult(
                allowed=remaining > 0,
                remaining=remaining,
                limit=config.max_requests,
                reset_at=entry.window_start + effective_window,
                violations=entry.violations,
            )
    
    def cleanup(self) -> int:
        """Remove expired entries."""
        now = self.now()
        removed = 0
        
        with self._lock:
            # Find stale entries (no activity for 2x max backoff)
            stale_threshold = now - (MAX_ENTRIES * 2)  # Use a reasonable TTL
            stale_keys = []
            
            for key, entry in self._entries.items():
                # Entry is stale if:
                # 1. Last access was long ago AND
                # 2. Not currently blocked
                if entry.last_access < stale_threshold and entry.blocked_until < now:
                    stale_keys.append(key)
            
            for key in stale_keys:
                del self._entries[key]
                removed += 1
            
            self._cleanup_count += 1
        
        return removed
    
    def health_check(self) -> bool:
        """Memory backend is always healthy."""
        return True
    
    def _ensure_capacity(self) -> None:
        """Evict oldest entries if at capacity (must hold lock)."""
        while len(self._entries) >= self.max_entries:
            # Pop oldest (first) entry
            oldest_key = next(iter(self._entries))
            del self._entries[oldest_key]
            self._eviction_count += 1
    
    def _maybe_cleanup(self, now: float, config: RateLimitConfig) -> None:
        """Periodic cleanup of expired entries (must hold lock)."""
        if now - self._last_cleanup < self.cleanup_interval:
            return
        
        self._last_cleanup = now
        
        # Remove entries that have been inactive for 2x max backoff window
        ttl = config.max_backoff_seconds * 2
        stale_keys = []
        
        for key, entry in self._entries.items():
            if now - entry.last_access > ttl and entry.blocked_until < now:
                stale_keys.append(key)
        
        for key in stale_keys:
            del self._entries[key]
    
    # Stats methods for monitoring
    
    def get_entry_count(self) -> int:
        """Get current number of entries."""
        with self._lock:
            return len(self._entries)
    
    def get_eviction_count(self) -> int:
        """Get total number of LRU evictions."""
        return self._eviction_count
    
    def get_stats(self) -> dict:
        """Get backend statistics."""
        with self._lock:
            return {
                "entries": len(self._entries),
                "max_entries": self.max_entries,
                "evictions": self._eviction_count,
                "cleanups": self._cleanup_count,
            }

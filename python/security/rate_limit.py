"""
Rate Limiting Module - Brute Force Protection

Security Requirements:
- Login attempts MUST be rate limited per IP
- API requests MUST be rate limited
- Limits MUST be configurable via environment
- Rate limit state MUST persist across requests (in-memory or Redis)
"""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from functools import wraps


# Default rate limits (configurable via ENV)
RATE_LIMIT_LOGIN_MAX = int(os.environ.get("RATE_LIMIT_LOGIN_MAX", "5"))
RATE_LIMIT_LOGIN_WINDOW = int(os.environ.get("RATE_LIMIT_LOGIN_WINDOW", "60"))  # seconds

RATE_LIMIT_API_MAX = int(os.environ.get("RATE_LIMIT_API_MAX", "60"))
RATE_LIMIT_API_WINDOW = int(os.environ.get("RATE_LIMIT_API_WINDOW", "60"))  # seconds

# Backoff multiplier for repeated violations
BACKOFF_MULTIPLIER = float(os.environ.get("RATE_LIMIT_BACKOFF", "2.0"))
MAX_BACKOFF_WINDOW = int(os.environ.get("RATE_LIMIT_MAX_BACKOFF", "3600"))  # 1 hour max


@dataclass
class RateLimitEntry:
    """Tracks rate limit state for a single key (IP address)."""
    count: int = 0
    window_start: float = field(default_factory=time.time)
    violations: int = 0  # Number of times limit was exceeded
    blocked_until: float = 0.0


class RateLimiter:
    """
    In-memory rate limiter with sliding window.
    
    Thread-safe implementation suitable for single-process deployments.
    For multi-process/distributed, use Redis-based rate limiting.
    """
    
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        *,
        enable_backoff: bool = True,
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
            enable_backoff: Whether to increase window on repeated violations
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enable_backoff = enable_backoff
        self._entries: Dict[str, RateLimitEntry] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # Cleanup old entries every 5 minutes
        self._last_cleanup = time.time()
    
    def is_allowed(self, key: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a request is allowed for the given key.
        
        Args:
            key: Identifier (usually IP address)
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            retry_after_seconds is None if allowed, or seconds until retry if blocked
        """
        now = time.time()
        
        with self._lock:
            self._maybe_cleanup(now)
            
            if key not in self._entries:
                self._entries[key] = RateLimitEntry(count=1, window_start=now)
                return True, None
            
            entry = self._entries[key]
            
            # Check if currently blocked due to backoff
            if entry.blocked_until > now:
                retry_after = int(entry.blocked_until - now) + 1
                return False, retry_after
            
            # Calculate effective window (may be extended due to backoff)
            effective_window = self.window_seconds
            if self.enable_backoff and entry.violations > 0:
                effective_window = min(
                    self.window_seconds * (BACKOFF_MULTIPLIER ** entry.violations),
                    MAX_BACKOFF_WINDOW
                )
            
            # Check if window has expired
            if now - entry.window_start >= effective_window:
                # Reset window
                entry.count = 1
                entry.window_start = now
                return True, None
            
            # Check if under limit
            if entry.count < self.max_requests:
                entry.count += 1
                return True, None
            
            # Rate limit exceeded
            entry.violations += 1
            
            # Calculate backoff block time
            if self.enable_backoff:
                block_duration = min(
                    effective_window * BACKOFF_MULTIPLIER,
                    MAX_BACKOFF_WINDOW
                )
                entry.blocked_until = now + block_duration
                retry_after = int(block_duration) + 1
            else:
                retry_after = int(effective_window - (now - entry.window_start)) + 1
            
            return False, retry_after
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key (e.g., after successful login)."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key in current window."""
        with self._lock:
            if key not in self._entries:
                return self.max_requests
            
            entry = self._entries[key]
            now = time.time()
            
            # Window expired
            if now - entry.window_start >= self.window_seconds:
                return self.max_requests
            
            return max(0, self.max_requests - entry.count)
    
    def _maybe_cleanup(self, now: float) -> None:
        """Remove stale entries to prevent memory leak."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        stale_keys = []
        
        for key, entry in self._entries.items():
            # Remove entries that have been inactive for 2x the max backoff window
            if now - entry.window_start > MAX_BACKOFF_WINDOW * 2:
                if entry.blocked_until < now:
                    stale_keys.append(key)
        
        for key in stale_keys:
            del self._entries[key]


# Global rate limiters
_login_limiter: Optional[RateLimiter] = None
_api_limiter: Optional[RateLimiter] = None


def get_login_limiter() -> RateLimiter:
    """Get or create the login rate limiter."""
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = RateLimiter(
            max_requests=RATE_LIMIT_LOGIN_MAX,
            window_seconds=RATE_LIMIT_LOGIN_WINDOW,
            enable_backoff=True,
        )
    return _login_limiter


def get_api_limiter() -> RateLimiter:
    """Get or create the API rate limiter."""
    global _api_limiter
    if _api_limiter is None:
        _api_limiter = RateLimiter(
            max_requests=RATE_LIMIT_API_MAX,
            window_seconds=RATE_LIMIT_API_WINDOW,
            enable_backoff=False,
        )
    return _api_limiter


def check_login_rate_limit(ip_address: str) -> Tuple[bool, Optional[int]]:
    """
    Check if login attempt is allowed for IP.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    return get_login_limiter().is_allowed(ip_address)


def check_api_rate_limit(ip_address: str) -> Tuple[bool, Optional[int]]:
    """
    Check if API request is allowed for IP.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    return get_api_limiter().is_allowed(ip_address)


def reset_login_rate_limit(ip_address: str) -> None:
    """Reset login rate limit after successful login."""
    get_login_limiter().reset(ip_address)


def rate_limit_response(retry_after: int) -> Tuple[str, int, dict]:
    """
    Generate a 429 Too Many Requests response.
    
    Args:
        retry_after: Seconds until retry is allowed
        
    Returns:
        Tuple of (body, status_code, headers)
    """
    return (
        f"Too many requests. Please try again in {retry_after} seconds.",
        429,
        {"Retry-After": str(retry_after)}
    )

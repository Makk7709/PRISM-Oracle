"""
Rate Limiting Interfaces and Types

Defines the contract for rate limit backends and configuration.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, Callable


class FailMode(Enum):
    """Behavior when backend is unavailable."""
    FAIL_OPEN = "fail_open"      # Allow requests (dangerous in prod)
    FAIL_CLOSED = "fail_closed"  # Deny requests (safe default)


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    name: str                           # e.g., "login", "api"
    max_requests: int = 5               # Requests per window
    window_seconds: int = 60            # Time window
    enable_backoff: bool = True         # Exponential backoff on violations
    backoff_multiplier: float = 2.0     # Backoff factor
    max_backoff_seconds: int = 3600     # Max backoff ceiling (1 hour)
    
    @classmethod
    def from_env(cls, name: str) -> "RateLimitConfig":
        """Load config from environment variables."""
        prefix = f"KOREV_RATE_LIMIT_{name.upper()}_"
        return cls(
            name=name,
            max_requests=int(os.environ.get(f"{prefix}MAX", "5")),
            window_seconds=int(os.environ.get(f"{prefix}WINDOW", "60")),
            enable_backoff=os.environ.get(f"{prefix}BACKOFF", "true").lower() == "true",
            backoff_multiplier=float(os.environ.get(f"{prefix}BACKOFF_MULT", "2.0")),
            max_backoff_seconds=int(os.environ.get(f"{prefix}MAX_BACKOFF", "3600")),
        )


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int                      # Requests remaining in window
    limit: int                          # Max requests allowed
    reset_at: float                     # Unix timestamp when window resets
    retry_after: Optional[int] = None   # Seconds until retry (if blocked)
    violations: int = 0                 # Number of violations for this key


class RateLimitBackend(ABC):
    """
    Abstract base class for rate limit storage backends.
    
    Implementations must be thread-safe and handle their own locking.
    """
    
    def __init__(
        self,
        fail_mode: FailMode = FailMode.FAIL_CLOSED,
        now_fn: Optional[Callable[[], float]] = None,
    ):
        """
        Initialize backend.
        
        Args:
            fail_mode: Behavior when backend is unavailable
            now_fn: Function returning current time (for testing)
        """
        self.fail_mode = fail_mode
        self._now_fn = now_fn or self._default_now
    
    @staticmethod
    def _default_now() -> float:
        """Default time provider."""
        import time
        return time.time()
    
    def now(self) -> float:
        """Get current timestamp (injectable for tests)."""
        return self._now_fn()
    
    @abstractmethod
    def check(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> RateLimitResult:
        """
        Check if request is allowed and increment counter.
        
        Args:
            key: Unique identifier (e.g., "login:192.168.1.1")
            config: Rate limit configuration
            
        Returns:
            RateLimitResult with allow/deny decision and metadata
        """
        pass  # pragma: no cover
    
    @abstractmethod
    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key (e.g., after successful login).
        
        Args:
            key: Key to reset
        """
        pass  # pragma: no cover
    
    @abstractmethod
    def get_info(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """
        Get current rate limit info without incrementing counter.
        
        Args:
            key: Key to check
            config: Rate limit configuration
            
        Returns:
            Current rate limit state
        """
        pass  # pragma: no cover
    
    @abstractmethod
    def cleanup(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        pass  # pragma: no cover
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if backend is healthy/available.
        
        Returns:
            True if backend is operational
        """
        pass  # pragma: no cover


def get_fail_mode() -> FailMode:
    """Get fail mode from environment."""
    mode = os.environ.get("KOREV_RATE_LIMIT_FAIL_MODE", "fail_closed").lower()
    if mode == "fail_open":
        return FailMode.FAIL_OPEN
    return FailMode.FAIL_CLOSED


def is_production() -> bool:
    """Check if running in production mode."""
    return os.environ.get("KOREV_PRODUCTION", "").lower() in ("true", "1", "yes")

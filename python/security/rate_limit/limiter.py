"""
Rate Limiter - Main API

Provides unified interface for rate limiting with pluggable backends.
Automatically selects backend based on environment configuration.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, Callable

from python.security.rate_limit.interfaces import (
    RateLimitBackend,
    RateLimitConfig,
    RateLimitResult,
    FailMode,
    get_fail_mode,
    is_production,
)

logger = logging.getLogger(__name__)

# Backend selection
BACKEND_MEMORY = "memory"
BACKEND_REDIS = "redis"


@dataclass
class RateLimitInfo:
    """Rate limit information for responses."""
    allowed: bool
    retry_after: Optional[int]
    remaining: int
    limit: int
    reset_at: float
    
    def to_headers(self) -> Dict[str, str]:
        """Generate X-RateLimit-* headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers


class RateLimiter:
    """
    Main rate limiter class.
    
    Supports multiple named rate limits (e.g., "login", "api") with
    different configurations. Uses pluggable backend (memory or redis).
    """
    
    def __init__(
        self,
        backend: Optional[RateLimitBackend] = None,
        configs: Optional[Dict[str, RateLimitConfig]] = None,
    ):
        """
        Initialize rate limiter.
        
        Args:
            backend: Storage backend (auto-selected if None)
            configs: Named rate limit configurations
        """
        self._backend = backend or self._create_default_backend()
        self._configs = configs or {}
        
        # Add default configs
        if "login" not in self._configs:
            self._configs["login"] = RateLimitConfig(
                name="login",
                max_requests=int(os.environ.get("RATE_LIMIT_LOGIN_MAX", "5")),
                window_seconds=int(os.environ.get("RATE_LIMIT_LOGIN_WINDOW", "60")),
                enable_backoff=True,
            )
        
        if "api" not in self._configs:
            self._configs["api"] = RateLimitConfig(
                name="api",
                max_requests=int(os.environ.get("RATE_LIMIT_API_MAX", "60")),
                window_seconds=int(os.environ.get("RATE_LIMIT_API_WINDOW", "60")),
                enable_backoff=False,
            )
    
    @staticmethod
    def _create_default_backend() -> RateLimitBackend:
        """Create default backend based on environment."""
        backend_type = os.environ.get("KOREV_RATE_LIMIT_BACKEND", "").lower()
        fail_mode = get_fail_mode()
        
        # Auto-select: Redis in production, memory in dev
        if not backend_type:
            backend_type = BACKEND_REDIS if is_production() else BACKEND_MEMORY
        
        if backend_type == BACKEND_REDIS:
            # Try Redis, fall back to memory if unavailable
            from python.security.rate_limit.redis_backend import (
                RedisBackend,
                is_redis_available,
            )
            
            if is_redis_available():
                logger.info("Using Redis backend for rate limiting")
                return RedisBackend(fail_mode=fail_mode)
            else:
                if is_production():
                    logger.warning(
                        "Redis unavailable in production - using memory backend. "
                        "Rate limiting will NOT be shared across workers!"
                    )
                else:
                    logger.info("Redis unavailable - using memory backend")
                
                from python.security.rate_limit.memory_backend import MemoryBackend
                return MemoryBackend(fail_mode=fail_mode)
        
        else:
            from python.security.rate_limit.memory_backend import MemoryBackend
            logger.info("Using memory backend for rate limiting")
            return MemoryBackend(fail_mode=fail_mode)
    
    def check(
        self,
        name: str,
        key: str,
        config: Optional[RateLimitConfig] = None,
    ) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is allowed.
        
        Args:
            name: Rate limit name (e.g., "login", "api")
            key: Unique key (e.g., IP address)
            config: Override configuration (uses default for name if None)
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        cfg = config or self._configs.get(name)
        if cfg is None:
            cfg = RateLimitConfig(name=name)
        
        # Create combined key
        full_key = f"{name}:{key}"
        
        result = self._backend.check(full_key, cfg)
        
        info = RateLimitInfo(
            allowed=result.allowed,
            retry_after=result.retry_after,
            remaining=result.remaining,
            limit=result.limit,
            reset_at=result.reset_at,
        )
        
        return result.allowed, info
    
    def reset(self, name: str, key: str) -> None:
        """
        Reset rate limit for a key.
        
        Args:
            name: Rate limit name
            key: Key to reset
        """
        full_key = f"{name}:{key}"
        self._backend.reset(full_key)
    
    def get_info(
        self,
        name: str,
        key: str,
        config: Optional[RateLimitConfig] = None,
    ) -> RateLimitInfo:
        """
        Get rate limit info without incrementing counter.
        
        Args:
            name: Rate limit name
            key: Key to check
            config: Override configuration
            
        Returns:
            Current rate limit info
        """
        cfg = config or self._configs.get(name)
        if cfg is None:
            cfg = RateLimitConfig(name=name)
        
        full_key = f"{name}:{key}"
        result = self._backend.get_info(full_key, cfg)
        
        return RateLimitInfo(
            allowed=result.allowed,
            retry_after=result.retry_after,
            remaining=result.remaining,
            limit=result.limit,
            reset_at=result.reset_at,
        )
    
    def health_check(self) -> bool:
        """Check if backend is healthy."""
        return self._backend.health_check()
    
    def get_config(self, name: str) -> Optional[RateLimitConfig]:
        """Get configuration for a named rate limit."""
        return self._configs.get(name)
    
    @property
    def backend(self) -> RateLimitBackend:
        """Get the underlying backend (for testing/monitoring)."""
        return self._backend


# Global limiter instance
_limiter: Optional[RateLimiter] = None
_limiter_lock = None


def get_limiter() -> RateLimiter:
    """
    Get or create the global rate limiter instance.
    
    Thread-safe singleton pattern.
    """
    global _limiter, _limiter_lock
    
    if _limiter_lock is None:
        import threading
        _limiter_lock = threading.Lock()
    
    if _limiter is None:
        with _limiter_lock:
            # Double-check locking
            if _limiter is None:
                _limiter = RateLimiter()
    
    return _limiter


def reset_limiter() -> None:
    """Reset global limiter (for testing)."""
    global _limiter
    _limiter = None

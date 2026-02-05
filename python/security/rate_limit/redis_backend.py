"""
Redis Rate Limit Backend

Features:
- Shared state across workers/processes
- Atomic operations via Lua scripts
- TTL-based automatic expiration
- Suitable for production multi-worker deployments

Requires:
- Redis server
- redis-py package
"""

import os
import logging
from typing import Optional, Callable

from python.security.rate_limit.interfaces import (
    RateLimitBackend,
    RateLimitConfig,
    RateLimitResult,
    FailMode,
)

logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.environ.get("KOREV_REDIS_URL", "redis://localhost:6379/0")
REDIS_KEY_PREFIX = os.environ.get("KOREV_RATE_LIMIT_PREFIX", "rl:")
REDIS_CONNECT_TIMEOUT = float(os.environ.get("KOREV_REDIS_TIMEOUT", "2.0"))


# Lua script for atomic rate limit check
# Returns: [allowed(0/1), count, violations, blocked_until, window_start]
RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local max_requests = tonumber(ARGV[2])
local window_seconds = tonumber(ARGV[3])
local enable_backoff = tonumber(ARGV[4])
local backoff_mult = tonumber(ARGV[5])
local max_backoff = tonumber(ARGV[6])

-- Get current state
local data = redis.call('HMGET', key, 'count', 'window_start', 'violations', 'blocked_until')
local count = tonumber(data[1]) or 0
local window_start = tonumber(data[2]) or now
local violations = tonumber(data[3]) or 0
local blocked_until = tonumber(data[4]) or 0

-- Check if blocked
if blocked_until > now then
    return {0, count, violations, blocked_until, window_start}
end

-- Calculate effective window
local effective_window = window_seconds
if enable_backoff == 1 and violations > 0 then
    effective_window = math.min(window_seconds * math.pow(backoff_mult, violations), max_backoff)
end

-- Check if window expired
if now - window_start >= effective_window then
    count = 1
    window_start = now
    redis.call('HSET', key, 'count', count, 'window_start', window_start)
    redis.call('EXPIRE', key, math.ceil(max_backoff * 2))
    return {1, count, violations, 0, window_start}
end

-- Check if under limit
if count < max_requests then
    count = count + 1
    redis.call('HSET', key, 'count', count)
    redis.call('EXPIRE', key, math.ceil(max_backoff * 2))
    return {1, count, violations, 0, window_start}
end

-- Rate limit exceeded
violations = violations + 1
local new_blocked_until = 0

if enable_backoff == 1 then
    local block_duration = math.min(effective_window * backoff_mult, max_backoff)
    new_blocked_until = now + block_duration
    redis.call('HSET', key, 'violations', violations, 'blocked_until', new_blocked_until)
else
    redis.call('HSET', key, 'violations', violations)
end

redis.call('EXPIRE', key, math.ceil(max_backoff * 2))
return {0, count, violations, new_blocked_until, window_start}
"""


class RedisBackend(RateLimitBackend):
    """
    Redis-based rate limit backend for multi-worker deployments.
    
    Uses atomic Lua scripts to ensure consistency across concurrent requests.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = REDIS_KEY_PREFIX,
        connect_timeout: float = REDIS_CONNECT_TIMEOUT,
        fail_mode: FailMode = FailMode.FAIL_CLOSED,
        now_fn: Optional[Callable[[], float]] = None,
    ):
        """
        Initialize Redis backend.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for rate limit keys
            connect_timeout: Connection timeout in seconds
            fail_mode: Behavior when Redis is unavailable
            now_fn: Time provider for testing
        """
        super().__init__(fail_mode=fail_mode, now_fn=now_fn)
        
        self.redis_url = redis_url or REDIS_URL
        self.key_prefix = key_prefix
        self.connect_timeout = connect_timeout
        
        self._client = None
        self._lua_sha = None
        self._last_health_check = 0.0
        self._is_healthy = None
    
    def _get_client(self):
        """Get or create Redis client (lazy initialization)."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(
                    self.redis_url,
                    socket_connect_timeout=self.connect_timeout,
                    socket_timeout=self.connect_timeout,
                    decode_responses=False,
                )
                # Register Lua script
                self._lua_sha = self._client.script_load(RATE_LIMIT_LUA)
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client
    
    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"
    
    def _handle_failure(self, config: RateLimitConfig) -> RateLimitResult:
        """Handle backend failure according to fail_mode."""
        now = self.now()
        
        if self.fail_mode == FailMode.FAIL_OPEN:
            # Allow request but log warning
            logger.warning("Redis unavailable - FAIL_OPEN: allowing request")
            return RateLimitResult(
                allowed=True,
                remaining=config.max_requests,
                limit=config.max_requests,
                reset_at=now + config.window_seconds,
            )
        else:
            # Deny request (safe default)
            logger.warning("Redis unavailable - FAIL_CLOSED: denying request")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=config.max_requests,
                reset_at=now + 60,  # Retry in 1 minute
                retry_after=60,
            )
    
    def check(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> RateLimitResult:
        """Check if request is allowed using atomic Lua script."""
        now = self.now()
        redis_key = self._make_key(key)
        
        try:
            client = self._get_client()
            
            # Execute Lua script atomically
            result = client.evalsha(
                self._lua_sha,
                1,  # Number of keys
                redis_key,
                str(now),
                str(config.max_requests),
                str(config.window_seconds),
                "1" if config.enable_backoff else "0",
                str(config.backoff_multiplier),
                str(config.max_backoff_seconds),
            )
            
            # Parse result: [allowed, count, violations, blocked_until, window_start]
            allowed = int(result[0]) == 1
            count = int(result[1])
            violations = int(result[2])
            blocked_until = float(result[3])
            window_start = float(result[4])
            
            remaining = max(0, config.max_requests - count)
            
            # Calculate retry_after if blocked
            retry_after = None
            if not allowed:
                if blocked_until > now:
                    retry_after = int(blocked_until - now) + 1
                else:
                    # Calculate effective window
                    effective_window = config.window_seconds
                    if config.enable_backoff and violations > 0:
                        effective_window = min(
                            config.window_seconds * (config.backoff_multiplier ** violations),
                            config.max_backoff_seconds,
                        )
                    retry_after = int(effective_window - (now - window_start)) + 1
            
            reset_at = blocked_until if blocked_until > now else window_start + config.window_seconds
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                limit=config.max_requests,
                reset_at=reset_at,
                retry_after=retry_after,
                violations=violations,
            )
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            self._is_healthy = False
            return self._handle_failure(config)
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        redis_key = self._make_key(key)
        
        try:
            client = self._get_client()
            client.delete(redis_key)
        except Exception as e:
            logger.error(f"Redis rate limit reset failed: {e}")
    
    def get_info(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Get current rate limit info without incrementing."""
        now = self.now()
        redis_key = self._make_key(key)
        
        try:
            client = self._get_client()
            data = client.hmget(redis_key, 'count', 'window_start', 'violations', 'blocked_until')
            
            count = int(data[0]) if data[0] else 0
            window_start = float(data[1]) if data[1] else now
            violations = int(data[2]) if data[2] else 0
            blocked_until = float(data[3]) if data[3] else 0
            
            # Check if blocked
            if blocked_until > now:
                retry_after = int(blocked_until - now) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=config.max_requests,
                    reset_at=blocked_until,
                    retry_after=retry_after,
                    violations=violations,
                )
            
            # Calculate effective window
            effective_window = config.window_seconds
            if config.enable_backoff and violations > 0:
                effective_window = min(
                    config.window_seconds * (config.backoff_multiplier ** violations),
                    config.max_backoff_seconds,
                )
            
            # Check if window expired
            if now - window_start >= effective_window:
                return RateLimitResult(
                    allowed=True,
                    remaining=config.max_requests,
                    limit=config.max_requests,
                    reset_at=now + config.window_seconds,
                    violations=violations,
                )
            
            remaining = max(0, config.max_requests - count)
            return RateLimitResult(
                allowed=remaining > 0,
                remaining=remaining,
                limit=config.max_requests,
                reset_at=window_start + effective_window,
                violations=violations,
            )
            
        except Exception as e:
            logger.error(f"Redis get_info failed: {e}")
            return self._handle_failure(config)
    
    def cleanup(self) -> int:
        """Redis handles TTL automatically - this is a no-op."""
        return 0
    
    def health_check(self) -> bool:
        """Check if Redis is available."""
        try:
            client = self._get_client()
            client.ping()
            self._is_healthy = True
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._is_healthy = False
            return False


def is_redis_available(url: Optional[str] = None) -> bool:
    """Check if Redis is available at the configured URL."""
    try:
        import redis
        client = redis.from_url(
            url or REDIS_URL,
            socket_connect_timeout=1.0,
        )
        client.ping()
        return True
    except Exception:
        return False

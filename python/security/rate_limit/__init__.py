"""
Enterprise-Ready Rate Limiting Module

Supports:
- Pluggable backends: MEMORY (dev) / REDIS (prod)
- Proper IP extraction behind reverse proxy
- Exponential backoff with ceiling
- TTL-based cleanup
- Standard response headers (Retry-After, X-RateLimit-*)

Usage:
    from python.security.rate_limit import get_limiter, check_login_rate_limit
    
    # Direct API
    limiter = get_limiter()
    allowed, info = limiter.check("login", client_ip)
    
    # Convenience functions (backward compatible)
    allowed, retry_after = check_login_rate_limit(client_ip)
"""

from python.security.rate_limit.limiter import (
    RateLimiter,
    get_limiter,
    RateLimitInfo,
)
from python.security.rate_limit.interfaces import (
    RateLimitBackend,
    RateLimitConfig,
    FailMode,
)

# Backward-compatible API
from python.security.rate_limit.compat import (
    check_login_rate_limit,
    check_api_rate_limit,
    reset_login_rate_limit,
    rate_limit_response,
    get_login_limiter,
    get_api_limiter,
)

__all__ = [
    # New API
    "RateLimiter",
    "get_limiter",
    "RateLimitInfo",
    "RateLimitBackend",
    "RateLimitConfig",
    "FailMode",
    # Backward-compatible API
    "check_login_rate_limit",
    "check_api_rate_limit", 
    "reset_login_rate_limit",
    "rate_limit_response",
    "get_login_limiter",
    "get_api_limiter",
]

"""
Backward-Compatible API

Provides the old API for seamless migration:
- check_login_rate_limit(ip) -> (allowed, retry_after)
- reset_login_rate_limit(ip) -> None
- rate_limit_response(retry_after) -> (body, status, headers)

These wrap the new RateLimiter class.
"""

from typing import Optional, Tuple, Dict

from python.security.rate_limit.limiter import get_limiter, RateLimiter, RateLimitInfo


def check_login_rate_limit(ip_address: str) -> Tuple[bool, Optional[int]]:
    """
    Check if login attempt is allowed for IP.
    
    Backward-compatible wrapper for new limiter.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    limiter = get_limiter()
    allowed, info = limiter.check("login", ip_address)
    return allowed, info.retry_after


def check_api_rate_limit(ip_address: str) -> Tuple[bool, Optional[int]]:
    """
    Check if API request is allowed for IP.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    limiter = get_limiter()
    allowed, info = limiter.check("api", ip_address)
    return allowed, info.retry_after


def reset_login_rate_limit(ip_address: str) -> None:
    """Reset login rate limit after successful login."""
    limiter = get_limiter()
    limiter.reset("login", ip_address)


def rate_limit_response(
    retry_after: int,
    *,
    include_headers: bool = True,
) -> Tuple[str, int, Dict[str, str]]:
    """
    Generate a 429 Too Many Requests response.
    
    Args:
        retry_after: Seconds until retry is allowed
        include_headers: Include X-RateLimit-* headers
        
    Returns:
        Tuple of (body, status_code, headers)
    """
    headers = {
        "Retry-After": str(retry_after),
    }
    
    if include_headers:
        # Add standard rate limit headers
        headers["X-RateLimit-Remaining"] = "0"
    
    return (
        f"Too many requests. Please try again in {retry_after} seconds.",
        429,
        headers,
    )


def rate_limit_headers(info: RateLimitInfo) -> Dict[str, str]:
    """
    Generate rate limit headers from RateLimitInfo.
    
    Args:
        info: Rate limit information
        
    Returns:
        Dict of headers to add to response
    """
    return info.to_headers()


# Legacy class-based API compatibility
class _LegacyLimiter:
    """Legacy wrapper for old RateLimiter class interface."""
    
    def __init__(self):
        self._limiter = None
    
    @property
    def limiter(self) -> RateLimiter:
        if self._limiter is None:
            self._limiter = get_limiter()
        return self._limiter
    
    def is_allowed(self, key: str) -> Tuple[bool, Optional[int]]:
        return check_login_rate_limit(key)
    
    def reset(self, key: str) -> None:
        reset_login_rate_limit(key)


def get_login_limiter():
    """Get login rate limiter (legacy compatibility)."""
    return _LegacyLimiter()


def get_api_limiter():
    """Get API rate limiter (legacy compatibility)."""
    return _LegacyLimiter()

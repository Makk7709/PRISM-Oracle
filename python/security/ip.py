"""
IP Address Extraction Module

Provides reliable client IP extraction with proxy support.
Handles X-Forwarded-For, X-Real-IP headers when behind reverse proxy.
"""

import os
import re
from typing import Optional, List

# IPv4 and IPv6 validation patterns
IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

IPV6_PATTERN = re.compile(
    r'^(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|'
    r'(?:[0-9a-fA-F]{1,4}:){1,7}:|'
    r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|'
    r'(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|'
    r'(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|'
    r'(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|'
    r'(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|'
    r'[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}|'
    r':(?::[0-9a-fA-F]{1,4}){1,7}|'
    r'::(?:[fF]{4}:)?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|'
    r'(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$'
)

# Loopback addresses
LOOPBACK_ADDRESSES = {"127.0.0.1", "::1", "localhost"}

# Default fallback IP (used when extraction fails)
FALLBACK_IP = "0.0.0.0"


def is_valid_ip(ip: str) -> bool:
    """
    Validate if a string is a valid IPv4 or IPv6 address.
    
    Args:
        ip: String to validate
        
    Returns:
        True if valid IP address
    """
    if not ip or not isinstance(ip, str):
        return False
    
    ip = ip.strip()
    
    # Check IPv4
    if IPV4_PATTERN.match(ip):
        return True
    
    # Check IPv6
    if IPV6_PATTERN.match(ip):
        return True
    
    return False


def is_behind_proxy() -> bool:
    """Check if application is configured to be behind a reverse proxy."""
    return os.environ.get("KOREV_BEHIND_PROXY", "").lower() in ("true", "1", "yes")


def get_client_ip(
    request,
    *,
    behind_proxy: Optional[bool] = None,
    trust_proxy_headers: bool = True,
) -> str:
    """
    Extract the real client IP address from a request.
    
    When behind a reverse proxy (Caddy, Nginx, etc.), the client IP
    is in X-Forwarded-For or X-Real-IP headers. Otherwise, use remote_addr.
    
    Args:
        request: Flask request object
        behind_proxy: Override auto-detection of proxy mode
        trust_proxy_headers: Whether to trust proxy headers (disable for security)
        
    Returns:
        Client IP address string (validated)
        
    Security Note:
        When trust_proxy_headers=True, ensure your reverse proxy is configured
        to strip/overwrite X-Forwarded-For from client requests, otherwise
        attackers can spoof their IP by sending fake headers.
    """
    # Determine if we should check proxy headers
    check_proxy = behind_proxy if behind_proxy is not None else is_behind_proxy()
    
    if check_proxy and trust_proxy_headers:
        # Try X-Forwarded-For first (standard header)
        # Format: "client, proxy1, proxy2" - we want the first (client) IP
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            # Split by comma, take first IP (original client)
            ips = [ip.strip() for ip in xff.split(",")]
            for ip in ips:
                if is_valid_ip(ip):
                    return ip
        
        # Try X-Real-IP (Nginx convention)
        real_ip = request.headers.get("X-Real-IP", "")
        if real_ip and is_valid_ip(real_ip):
            return real_ip
    
    # Fall back to remote_addr
    remote_addr = getattr(request, "remote_addr", None)
    if remote_addr and is_valid_ip(remote_addr):
        return remote_addr
    
    # Last resort fallback
    return FALLBACK_IP


def parse_forwarded_for(header: str) -> List[str]:
    """
    Parse X-Forwarded-For header into list of IPs.
    
    Args:
        header: X-Forwarded-For header value
        
    Returns:
        List of valid IP addresses (in order: client first)
    """
    if not header:
        return []
    
    ips = []
    for part in header.split(","):
        ip = part.strip()
        if is_valid_ip(ip):
            ips.append(ip)
    
    return ips


def is_loopback(ip: str) -> bool:
    """Check if IP is a loopback address."""
    if not ip:
        return False
    
    ip = ip.strip().lower()
    
    # Check common loopback addresses
    if ip in LOOPBACK_ADDRESSES:
        return True
    
    # Check 127.x.x.x range
    if ip.startswith("127."):
        return True
    
    # Check IPv6 loopback
    if ip == "::1" or ip == "0:0:0:0:0:0:0:1":
        return True
    
    return False


def normalize_ip(ip: str) -> str:
    """
    Normalize an IP address for consistent storage.
    
    Args:
        ip: IP address string
        
    Returns:
        Normalized IP string
    """
    if not ip:
        return FALLBACK_IP
    
    ip = ip.strip().lower()
    
    # Handle IPv4-mapped IPv6 addresses (::ffff:192.168.1.1)
    if ip.startswith("::ffff:"):
        ipv4_part = ip[7:]
        if is_valid_ip(ipv4_part):
            return ipv4_part
    
    return ip

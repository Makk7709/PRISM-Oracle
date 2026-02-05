"""
IP Extraction Tests

Tests verify:
1. Direct client IP extraction (no proxy)
2. X-Forwarded-For handling (behind proxy)
3. X-Real-IP handling (Nginx convention)
4. Invalid IP rejection
5. Proxy mode detection
"""

import pytest
from unittest.mock import MagicMock, patch

from python.security.ip import (
    get_client_ip,
    is_valid_ip,
    is_behind_proxy,
    parse_forwarded_for,
    is_loopback,
    normalize_ip,
    FALLBACK_IP,
)


class TestIsValidIp:
    """Tests for IP validation."""
    
    @pytest.mark.parametrize("ip", [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
        "0.0.0.0",
        "255.255.255.255",
        "8.8.8.8",
    ])
    def test_valid_ipv4_addresses(self, ip):
        """Valid IPv4 addresses are accepted."""
        assert is_valid_ip(ip) is True
    
    @pytest.mark.parametrize("ip", [
        "::1",
        "fe80::1",
        "2001:db8::1",
        "::ffff:192.168.1.1",
    ])
    def test_valid_ipv6_addresses(self, ip):
        """Valid IPv6 addresses are accepted."""
        assert is_valid_ip(ip) is True
    
    @pytest.mark.parametrize("ip", [
        "",
        None,
        "invalid",
        "192.168.1",
        "192.168.1.1.1",
        "256.1.1.1",
        "192.168.1.a",
        "192.168.1.-1",
        "not.an.ip",
        "javascript:alert(1)",
        "<script>",
    ])
    def test_invalid_ip_addresses_rejected(self, ip):
        """Invalid IP addresses are rejected."""
        assert is_valid_ip(ip) is False


class TestGetClientIpNoProxy:
    """Tests for IP extraction without proxy."""
    
    def test_uses_remote_addr_when_no_proxy(self):
        """Without proxy, use request.remote_addr."""
        request = MagicMock()
        request.remote_addr = "192.168.1.100"
        request.headers = {}
        
        ip = get_client_ip(request, behind_proxy=False)
        
        assert ip == "192.168.1.100"
    
    def test_ignores_xff_when_proxy_disabled(self):
        """X-Forwarded-For is ignored when not behind proxy."""
        request = MagicMock()
        request.remote_addr = "10.0.0.1"
        request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        
        ip = get_client_ip(request, behind_proxy=False)
        
        assert ip == "10.0.0.1"  # Should use remote_addr, not XFF
    
    def test_returns_fallback_for_invalid_remote_addr(self):
        """Returns fallback if remote_addr is invalid."""
        request = MagicMock()
        request.remote_addr = "invalid"
        request.headers = {}
        
        ip = get_client_ip(request, behind_proxy=False)
        
        assert ip == FALLBACK_IP


class TestGetClientIpWithProxy:
    """Tests for IP extraction behind reverse proxy."""
    
    def test_uses_xff_first_hop_when_behind_proxy(self):
        """Behind proxy, use first IP from X-Forwarded-For."""
        request = MagicMock()
        request.remote_addr = "10.0.0.1"  # Proxy IP
        request.headers = MagicMock()
        request.headers.get = lambda k, d="": {
            "X-Forwarded-For": "203.0.113.50, 70.41.3.18, 10.0.0.1",
            "X-Real-IP": "",
        }.get(k, d)
        
        ip = get_client_ip(request, behind_proxy=True)
        
        assert ip == "203.0.113.50"  # First hop = real client
    
    def test_uses_x_real_ip_if_xff_empty(self):
        """Use X-Real-IP if X-Forwarded-For is empty."""
        request = MagicMock()
        request.remote_addr = "10.0.0.1"
        request.headers = MagicMock()
        request.headers.get = lambda k, d="": {
            "X-Forwarded-For": "",
            "X-Real-IP": "203.0.113.50",
        }.get(k, d)
        
        ip = get_client_ip(request, behind_proxy=True)
        
        assert ip == "203.0.113.50"
    
    def test_rejects_invalid_xff_ips(self):
        """Invalid IPs in X-Forwarded-For are skipped."""
        request = MagicMock()
        request.remote_addr = "10.0.0.1"
        request.headers = MagicMock()
        request.headers.get = lambda k, d="": {
            "X-Forwarded-For": "invalid, <script>, 192.168.1.100",
            "X-Real-IP": "",
        }.get(k, d)
        
        ip = get_client_ip(request, behind_proxy=True)
        
        assert ip == "192.168.1.100"  # First valid IP
    
    def test_falls_back_to_remote_addr_if_all_invalid(self):
        """Falls back to remote_addr if all XFF IPs are invalid."""
        request = MagicMock()
        request.remote_addr = "10.0.0.1"
        request.headers = MagicMock()
        request.headers.get = lambda k, d="": {
            "X-Forwarded-For": "invalid, also_invalid",
            "X-Real-IP": "still_invalid",
        }.get(k, d)
        
        ip = get_client_ip(request, behind_proxy=True)
        
        assert ip == "10.0.0.1"


class TestParseForwardedFor:
    """Tests for X-Forwarded-For parsing."""
    
    def test_parses_single_ip(self):
        """Single IP is parsed correctly."""
        ips = parse_forwarded_for("192.168.1.1")
        assert ips == ["192.168.1.1"]
    
    def test_parses_multiple_ips(self):
        """Multiple IPs are parsed in order."""
        ips = parse_forwarded_for("192.168.1.1, 10.0.0.1, 172.16.0.1")
        assert ips == ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
    
    def test_filters_invalid_ips(self):
        """Invalid IPs are filtered out."""
        ips = parse_forwarded_for("192.168.1.1, invalid, 10.0.0.1")
        assert ips == ["192.168.1.1", "10.0.0.1"]
    
    def test_empty_string_returns_empty_list(self):
        """Empty string returns empty list."""
        ips = parse_forwarded_for("")
        assert ips == []
    
    def test_handles_whitespace(self):
        """Handles extra whitespace."""
        ips = parse_forwarded_for("  192.168.1.1  ,  10.0.0.1  ")
        assert ips == ["192.168.1.1", "10.0.0.1"]


class TestIsLoopback:
    """Tests for loopback detection."""
    
    @pytest.mark.parametrize("ip", [
        "127.0.0.1",
        "127.0.0.2",
        "127.255.255.255",
        "::1",
        "localhost",
    ])
    def test_loopback_addresses_detected(self, ip):
        """Loopback addresses are detected."""
        assert is_loopback(ip) is True
    
    @pytest.mark.parametrize("ip", [
        "192.168.1.1",
        "10.0.0.1",
        "8.8.8.8",
        "::ffff:192.168.1.1",
    ])
    def test_non_loopback_addresses(self, ip):
        """Non-loopback addresses are not flagged."""
        assert is_loopback(ip) is False


class TestNormalizeIp:
    """Tests for IP normalization."""
    
    def test_ipv4_unchanged(self):
        """IPv4 addresses are unchanged."""
        assert normalize_ip("192.168.1.1") == "192.168.1.1"
    
    def test_ipv4_mapped_ipv6_converted(self):
        """IPv4-mapped IPv6 addresses are converted to IPv4."""
        assert normalize_ip("::ffff:192.168.1.1") == "192.168.1.1"
    
    def test_lowercased(self):
        """Addresses are lowercased."""
        assert normalize_ip("::FFFF:192.168.1.1") == "192.168.1.1"
    
    def test_stripped(self):
        """Whitespace is stripped."""
        assert normalize_ip("  192.168.1.1  ") == "192.168.1.1"
    
    def test_empty_returns_fallback(self):
        """Empty input returns fallback."""
        assert normalize_ip("") == FALLBACK_IP
        assert normalize_ip(None) == FALLBACK_IP


class TestIsBehindProxy:
    """Tests for proxy detection."""
    
    def test_detects_proxy_from_env(self):
        """Detects proxy mode from KOREV_BEHIND_PROXY env var."""
        with patch.dict("os.environ", {"KOREV_BEHIND_PROXY": "true"}):
            assert is_behind_proxy() is True
        
        with patch.dict("os.environ", {"KOREV_BEHIND_PROXY": "false"}):
            assert is_behind_proxy() is False
        
        with patch.dict("os.environ", {"KOREV_BEHIND_PROXY": ""}):
            assert is_behind_proxy() is False

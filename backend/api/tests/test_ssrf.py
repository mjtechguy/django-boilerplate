"""
Tests for SSRF (Server-Side Request Forgery) protection utilities.

Tests cover:
- Private IPv4 range blocking
- Private IPv6 range blocking
- Cloud metadata endpoint blocking
- DNS resolution validation
- Scheme validation (http vs https)
- Custom blocklist functionality
- Allowlist override functionality
- DNS rebinding protection
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from api.ssrf import (
    BlockedHostError,
    DNSResolutionError,
    InvalidSchemeError,
    PrivateIPError,
    SSRFProtectionError,
    is_blocked_hostname,
    is_private_ip,
    resolve_hostname,
    safe_request,
    validate_ip_addresses,
    validate_url_scheme,
    validate_webhook_url,
)


class TestIsPrivateIP:
    """Tests for private IP address detection."""

    # IPv4 Private Ranges
    @pytest.mark.parametrize(
        "ip_address",
        [
            "10.0.0.1",
            "10.255.255.255",
            "172.16.0.1",
            "172.31.255.255",
            "192.168.0.1",
            "192.168.255.255",
            "127.0.0.1",
            "127.255.255.255",
            "169.254.0.1",  # AWS/Azure metadata range
            "169.254.169.254",  # AWS/Azure/GCP metadata IP
            "0.0.0.0",
            "0.255.255.255",
            "100.64.0.0",  # Shared address space
            "100.127.255.255",
            "192.0.0.0",  # IETF Protocol Assignments
            "192.0.2.0",  # TEST-NET-1
            "198.18.0.0",  # Benchmarking
            "198.51.100.0",  # TEST-NET-2
            "203.0.113.0",  # TEST-NET-3
            "224.0.0.0",  # Multicast
            "239.255.255.255",
            "240.0.0.0",  # Reserved
            "255.255.255.254",
            "255.255.255.255",  # Broadcast
        ],
    )
    def test_detects_private_ipv4_ranges(self, ip_address):
        """Should detect all private IPv4 ranges as private."""
        assert is_private_ip(ip_address) is True

    # IPv6 Private Ranges
    @pytest.mark.parametrize(
        "ip_address",
        [
            "::1",  # Loopback
            "::",  # Unspecified
            "fc00::1",  # Unique local addresses
            "fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
            "fe80::1",  # Link-local
            "febf:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
            "ff00::1",  # Multicast
            "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
            "::ffff:127.0.0.1",  # IPv4-mapped IPv6 (loopback)
            "::ffff:10.0.0.1",  # IPv4-mapped IPv6 (private)
        ],
    )
    def test_detects_private_ipv6_ranges(self, ip_address):
        """Should detect all private IPv6 ranges as private."""
        assert is_private_ip(ip_address) is True

    # Public IPv4 addresses
    @pytest.mark.parametrize(
        "ip_address",
        [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "93.184.216.34",  # example.com
            "151.101.1.140",  # Reddit
            "13.107.42.14",  # Microsoft
        ],
    )
    def test_allows_public_ipv4_addresses(self, ip_address):
        """Should allow public IPv4 addresses."""
        assert is_private_ip(ip_address) is False

    # Public IPv6 addresses
    @pytest.mark.parametrize(
        "ip_address",
        [
            "2606:4700:4700::1111",  # Cloudflare DNS
            "2001:4860:4860::8888",  # Google DNS
            "2a00:1450:4001:800::200e",  # Google
        ],
    )
    def test_allows_public_ipv6_addresses(self, ip_address):
        """Should allow public IPv6 addresses."""
        assert is_private_ip(ip_address) is False

    def test_invalid_ip_treated_as_private(self):
        """Invalid IP addresses should be treated as private for safety."""
        assert is_private_ip("not-an-ip") is True
        assert is_private_ip("999.999.999.999") is True
        assert is_private_ip("") is True


class TestIsBlockedHostname:
    """Tests for blocked hostname detection."""

    @pytest.mark.parametrize(
        "hostname",
        [
            "metadata.google.internal",
            "169.254.169.254",
            "metadata",
            "localhost",
            "LOCALHOST",  # Case insensitive
            "Metadata.Google.Internal",  # Case insensitive
        ],
    )
    def test_blocks_default_hostnames(self, hostname):
        """Should block default blocked hostnames (metadata endpoints, localhost)."""
        assert is_blocked_hostname(hostname) is True

    def test_allows_non_blocked_hostnames(self):
        """Should allow hostnames not in blocklist."""
        assert is_blocked_hostname("example.com") is False
        assert is_blocked_hostname("api.example.com") is False
        assert is_blocked_hostname("google.com") is False

    @override_settings(WEBHOOK_BLOCKED_HOSTS=["internal.local", "admin.local"])
    def test_blocks_custom_hostnames(self):
        """Should block custom hostnames from settings."""
        assert is_blocked_hostname("internal.local") is True
        assert is_blocked_hostname("admin.local") is True
        assert is_blocked_hostname("INTERNAL.LOCAL") is True  # Case insensitive

    @override_settings(WEBHOOK_BLOCKED_HOSTS=["internal.local"])
    def test_allows_non_custom_blocked_hostnames(self):
        """Should allow hostnames not in custom blocklist."""
        assert is_blocked_hostname("example.com") is False


class TestValidateUrlScheme:
    """Tests for URL scheme validation."""

    @override_settings(WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_allows_https_by_default(self):
        """Should allow HTTPS URLs when only https is allowed."""
        # Should not raise
        validate_url_scheme("https://example.com/webhook")

    @override_settings(WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_blocks_http_when_only_https_allowed(self):
        """Should block HTTP URLs when only HTTPS is allowed."""
        with pytest.raises(InvalidSchemeError) as exc_info:
            validate_url_scheme("http://example.com/webhook")

        assert "http" in str(exc_info.value).lower()
        assert "https" in str(exc_info.value)

    @override_settings(WEBHOOK_ALLOWED_SCHEMES=["http", "https"])
    def test_allows_http_when_configured(self):
        """Should allow HTTP when configured in allowed schemes."""
        # Should not raise
        validate_url_scheme("http://example.com/webhook")
        validate_url_scheme("https://example.com/webhook")

    @override_settings(WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_blocks_other_schemes(self):
        """Should block non-HTTP(S) schemes."""
        with pytest.raises(InvalidSchemeError):
            validate_url_scheme("ftp://example.com/file")

        with pytest.raises(InvalidSchemeError):
            validate_url_scheme("file:///etc/passwd")

        with pytest.raises(InvalidSchemeError):
            validate_url_scheme("gopher://example.com")


class TestResolveHostname:
    """Tests for hostname resolution."""

    @patch("api.ssrf.socket.getaddrinfo")
    def test_resolves_hostname_to_ips(self, mock_getaddrinfo):
        """Should resolve hostname to list of IP addresses."""
        # Mock DNS response with multiple IPs
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("93.184.216.35", 0)),
        ]

        ips = resolve_hostname("example.com")

        assert len(ips) == 2
        assert "93.184.216.34" in ips
        assert "93.184.216.35" in ips
        mock_getaddrinfo.assert_called_once()

    @patch("api.ssrf.socket.getaddrinfo")
    def test_handles_ipv6_resolution(self, mock_getaddrinfo):
        """Should handle IPv6 address resolution."""
        mock_getaddrinfo.return_value = [
            (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 0, 0, 0)),
        ]

        ips = resolve_hostname("example.com")

        assert len(ips) == 1
        assert "2606:2800:220:1:248:1893:25c8:1946" in ips

    @patch("api.ssrf.socket.getaddrinfo")
    def test_deduplicates_ip_addresses(self, mock_getaddrinfo):
        """Should deduplicate IP addresses from DNS response."""
        # Mock response with duplicate IPs
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("93.184.216.35", 0)),
        ]

        ips = resolve_hostname("example.com")

        assert len(ips) == 2

    @patch("api.ssrf.socket.getaddrinfo")
    def test_raises_on_dns_failure(self, mock_getaddrinfo):
        """Should raise DNSResolutionError when DNS resolution fails."""
        import socket

        mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")

        with pytest.raises(DNSResolutionError) as exc_info:
            resolve_hostname("nonexistent.invalid")

        assert "nonexistent.invalid" in str(exc_info.value)

    @patch("api.ssrf.socket.getaddrinfo")
    def test_raises_on_empty_response(self, mock_getaddrinfo):
        """Should raise DNSResolutionError when no IPs returned."""
        mock_getaddrinfo.return_value = []

        with pytest.raises(DNSResolutionError) as exc_info:
            resolve_hostname("example.com")

        assert "no IP addresses" in str(exc_info.value)


class TestValidateIPAddresses:
    """Tests for IP address validation."""

    def test_allows_public_ips(self):
        """Should allow public IP addresses."""
        # Should not raise
        validate_ip_addresses("example.com", ["93.184.216.34"])
        validate_ip_addresses("google.com", ["8.8.8.8", "8.8.4.4"])

    def test_blocks_private_ipv4(self):
        """Should block private IPv4 addresses."""
        with pytest.raises(PrivateIPError) as exc_info:
            validate_ip_addresses("internal.example.com", ["192.168.1.1"])

        assert "192.168.1.1" in str(exc_info.value)
        assert "internal.example.com" in str(exc_info.value)

    def test_blocks_localhost(self):
        """Should block localhost IP."""
        with pytest.raises(PrivateIPError):
            validate_ip_addresses("localhost", ["127.0.0.1"])

    def test_blocks_metadata_endpoint(self):
        """Should block cloud metadata endpoint IP."""
        with pytest.raises(PrivateIPError):
            validate_ip_addresses("metadata.local", ["169.254.169.254"])

    def test_blocks_private_ipv6(self):
        """Should block private IPv6 addresses."""
        with pytest.raises(PrivateIPError):
            validate_ip_addresses("internal.example.com", ["::1"])

        with pytest.raises(PrivateIPError):
            validate_ip_addresses("internal.example.com", ["fc00::1"])

    def test_blocks_if_any_ip_is_private(self):
        """Should block if ANY resolved IP is private."""
        with pytest.raises(PrivateIPError) as exc_info:
            # Mix of public and private IPs
            validate_ip_addresses("mixed.example.com", ["8.8.8.8", "192.168.1.1"])

        assert "192.168.1.1" in str(exc_info.value)


class TestValidateWebhookUrl:
    """Tests for comprehensive webhook URL validation."""

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.resolve_hostname")
    def test_validates_public_url_successfully(self, mock_resolve):
        """Should successfully validate a public HTTPS URL."""
        mock_resolve.return_value = ["93.184.216.34"]

        hostname, ips = validate_webhook_url("https://example.com/webhook")

        assert hostname == "example.com"
        assert ips == ["93.184.216.34"]
        mock_resolve.assert_called_once_with("example.com")

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=True, WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_blocks_http_scheme(self):
        """Should block HTTP URLs when only HTTPS is allowed."""
        with pytest.raises(InvalidSchemeError):
            validate_webhook_url("http://example.com/webhook")

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=True, WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_blocks_metadata_hostname(self):
        """Should block cloud metadata hostnames."""
        with pytest.raises(BlockedHostError) as exc_info:
            validate_webhook_url("https://metadata.google.internal/webhook")

        assert "metadata.google.internal" in str(exc_info.value).lower()

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=True, WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_blocks_localhost_hostname(self):
        """Should block localhost hostname."""
        with pytest.raises(BlockedHostError):
            validate_webhook_url("https://localhost/webhook")

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.resolve_hostname")
    def test_blocks_url_resolving_to_private_ip(self, mock_resolve):
        """Should block URLs that resolve to private IPs (DNS rebinding protection)."""
        mock_resolve.return_value = ["192.168.1.1"]

        with pytest.raises(PrivateIPError) as exc_info:
            validate_webhook_url("https://evil.example.com/webhook")

        assert "192.168.1.1" in str(exc_info.value)

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.resolve_hostname")
    def test_blocks_url_resolving_to_metadata_ip(self, mock_resolve):
        """Should block URLs that resolve to metadata endpoint IP."""
        mock_resolve.return_value = ["169.254.169.254"]

        with pytest.raises(PrivateIPError):
            validate_webhook_url("https://evil.example.com/webhook")

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCKED_HOSTS=["internal.local", "admin.local"],
    )
    def test_blocks_custom_blocklist_hostnames(self):
        """Should block hostnames in custom blocklist."""
        with pytest.raises(BlockedHostError):
            validate_webhook_url("https://internal.local/webhook")

        with pytest.raises(BlockedHostError):
            validate_webhook_url("https://admin.local/webhook")

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_ALLOWED_HOSTS=["test.local", "staging.local"],
    )
    def test_allowlist_bypasses_all_checks(self):
        """Allowlist should bypass all SSRF checks (for testing)."""
        # Should not raise, even though it would normally be blocked
        hostname, ips = validate_webhook_url("https://test.local/webhook")

        assert hostname == "test.local"
        assert ips == []  # Empty when allowlist bypasses checks

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_ALLOWED_HOSTS=["localhost"],
    )
    def test_allowlist_overrides_default_blocklist(self):
        """Allowlist should override even default blocked hosts."""
        # localhost is in default blocklist, but allowlist should override
        hostname, ips = validate_webhook_url("https://localhost/webhook")

        assert hostname == "localhost"
        assert ips == []

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=False)
    def test_disabled_protection_allows_all(self):
        """When SSRF protection is disabled, all URLs should be allowed."""
        hostname, ips = validate_webhook_url("http://localhost/webhook")

        assert hostname == "localhost"
        assert ips == []  # Empty when protection is disabled

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=False,
    )
    @patch("api.ssrf.resolve_hostname")
    def test_disabled_private_ip_blocking_allows_private_ips(self, mock_resolve):
        """When WEBHOOK_BLOCK_PRIVATE_IPS is False, private IPs should be allowed."""
        mock_resolve.return_value = ["192.168.1.1"]

        hostname, ips = validate_webhook_url("https://internal.example.com/webhook")

        assert hostname == "internal.example.com"
        assert ips == ["192.168.1.1"]

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=True, WEBHOOK_ALLOWED_SCHEMES=["https"])
    def test_blocks_url_without_hostname(self):
        """Should block URLs without a valid hostname."""
        with pytest.raises(BlockedHostError):
            validate_webhook_url("https:///webhook")

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=True, WEBHOOK_ALLOWED_SCHEMES=["https"])
    @patch("api.ssrf.resolve_hostname")
    def test_handles_dns_resolution_errors(self, mock_resolve):
        """Should raise DNSResolutionError when DNS fails."""
        mock_resolve.side_effect = DNSResolutionError("DNS lookup failed")

        with pytest.raises(DNSResolutionError):
            validate_webhook_url("https://nonexistent.invalid/webhook")


class TestSafeRequest:
    """Tests for safe_request wrapper function."""

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
        WEBHOOK_REQUEST_TIMEOUT=30,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_makes_request_to_resolved_ip(self, mock_resolve, mock_request):
        """Should make HTTP request to resolved IP with original Host header."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = safe_request("https://example.com/webhook", json={"test": "data"})

        assert result == mock_response
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]

        # Should request to IP, not hostname
        assert "93.184.216.34" in call_kwargs["url"]

        # Should include original Host header
        assert call_kwargs["headers"]["Host"] == "example.com"

        # Should include payload
        assert call_kwargs["json"] == {"test": "data"}

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.resolve_hostname")
    def test_raises_on_private_ip_resolution(self, mock_resolve):
        """Should raise PrivateIPError if URL resolves to private IP."""
        mock_resolve.return_value = ["192.168.1.1"]

        with pytest.raises(PrivateIPError):
            safe_request("https://evil.example.com/webhook")

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_REQUEST_TIMEOUT=45,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_uses_configured_timeout(self, mock_resolve, mock_request):
        """Should use timeout from settings."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_request.return_value = MagicMock()

        safe_request("https://example.com/webhook")

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["timeout"] == 45

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_REQUEST_TIMEOUT=30,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_allows_custom_timeout_override(self, mock_resolve, mock_request):
        """Should allow timeout to be overridden in function call."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_request.return_value = MagicMock()

        safe_request("https://example.com/webhook", timeout=60)

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["timeout"] == 60

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_preserves_url_path_and_query(self, mock_resolve, mock_request):
        """Should preserve URL path and query parameters."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_request.return_value = MagicMock()

        safe_request("https://example.com/webhook/path?key=value&foo=bar")

        call_kwargs = mock_request.call_args[1]
        assert "/webhook/path" in call_kwargs["url"]
        assert "key=value" in call_kwargs["url"]
        assert "foo=bar" in call_kwargs["url"]

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_preserves_port_in_url(self, mock_resolve, mock_request):
        """Should preserve custom port in URL."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_request.return_value = MagicMock()

        safe_request("https://example.com:8443/webhook")

        call_kwargs = mock_request.call_args[1]
        assert "93.184.216.34:8443" in call_kwargs["url"]

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_merges_custom_headers_with_host_header(self, mock_resolve, mock_request):
        """Should merge custom headers with required Host header."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_request.return_value = MagicMock()

        custom_headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        safe_request("https://example.com/webhook", headers=custom_headers)

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["headers"]["Host"] == "example.com"
        assert call_kwargs["headers"]["Authorization"] == "Bearer token123"
        assert call_kwargs["headers"]["X-Custom"] == "value"

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_ALLOWED_HOSTS=["test.local"],
    )
    @patch("api.ssrf.requests.request")
    def test_direct_request_when_allowlist_used(self, mock_request):
        """Should make direct request when allowlist bypasses IP resolution."""
        mock_request.return_value = MagicMock()

        safe_request("https://test.local/webhook")

        call_kwargs = mock_request.call_args[1]
        # Should use original URL, not IP
        assert "test.local" in call_kwargs["url"]

    @override_settings(WEBHOOK_SSRF_PROTECTION_ENABLED=False)
    @patch("api.ssrf.requests.request")
    def test_direct_request_when_protection_disabled(self, mock_request):
        """Should make direct request when SSRF protection is disabled."""
        mock_request.return_value = MagicMock()

        safe_request("http://localhost/webhook")

        call_kwargs = mock_request.call_args[1]
        # Should use original URL
        assert "localhost" in call_kwargs["url"]

    @override_settings(
        WEBHOOK_SSRF_PROTECTION_ENABLED=True,
        WEBHOOK_ALLOWED_SCHEMES=["https"],
        WEBHOOK_BLOCK_PRIVATE_IPS=True,
    )
    @patch("api.ssrf.requests.request")
    @patch("api.ssrf.resolve_hostname")
    def test_supports_different_http_methods(self, mock_resolve, mock_request):
        """Should support different HTTP methods."""
        mock_resolve.return_value = ["93.184.216.34"]
        mock_request.return_value = MagicMock()

        safe_request("https://example.com/webhook", method="GET")

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["method"] == "GET"


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """All SSRF exceptions should inherit from SSRFProtectionError."""
        assert issubclass(BlockedHostError, SSRFProtectionError)
        assert issubclass(PrivateIPError, SSRFProtectionError)
        assert issubclass(DNSResolutionError, SSRFProtectionError)
        assert issubclass(InvalidSchemeError, SSRFProtectionError)

    def test_base_exception_inherits_from_exception(self):
        """Base SSRFProtectionError should inherit from Exception."""
        assert issubclass(SSRFProtectionError, Exception)

    def test_exceptions_are_catchable(self):
        """SSRF exceptions should be catchable as SSRFProtectionError."""
        try:
            raise BlockedHostError("test")
        except SSRFProtectionError:
            pass  # Should catch successfully

        try:
            raise PrivateIPError("test")
        except SSRFProtectionError:
            pass

        try:
            raise DNSResolutionError("test")
        except SSRFProtectionError:
            pass

        try:
            raise InvalidSchemeError("test")
        except SSRFProtectionError:
            pass


class TestSSRFProtectionSettings:
    """Tests to verify SSRF protection settings are properly configured."""

    def test_ssrf_settings_present(self):
        """SSRF protection settings should be present in Django settings."""
        from django.conf import settings

        assert hasattr(settings, "WEBHOOK_SSRF_PROTECTION_ENABLED")
        assert hasattr(settings, "WEBHOOK_BLOCK_PRIVATE_IPS")
        assert hasattr(settings, "WEBHOOK_REQUEST_TIMEOUT")
        assert hasattr(settings, "WEBHOOK_ALLOWED_SCHEMES")
        assert hasattr(settings, "WEBHOOK_BLOCKED_HOSTS")
        assert hasattr(settings, "WEBHOOK_ALLOWED_HOSTS")

    def test_ssrf_default_values(self):
        """SSRF protection settings should have secure defaults."""
        from django.conf import settings

        # Protection should be enabled by default
        assert settings.WEBHOOK_SSRF_PROTECTION_ENABLED is True

        # Private IPs should be blocked by default
        assert settings.WEBHOOK_BLOCK_PRIVATE_IPS is True

        # Timeout should be reasonable
        assert settings.WEBHOOK_REQUEST_TIMEOUT > 0
        assert settings.WEBHOOK_REQUEST_TIMEOUT <= 120

        # Only HTTPS should be allowed by default
        assert "https" in settings.WEBHOOK_ALLOWED_SCHEMES

    def test_ssrf_settings_types(self):
        """SSRF protection settings should have correct types."""
        from django.conf import settings

        assert isinstance(settings.WEBHOOK_SSRF_PROTECTION_ENABLED, bool)
        assert isinstance(settings.WEBHOOK_BLOCK_PRIVATE_IPS, bool)
        assert isinstance(settings.WEBHOOK_REQUEST_TIMEOUT, int)
        assert isinstance(settings.WEBHOOK_ALLOWED_SCHEMES, list)
        assert isinstance(settings.WEBHOOK_BLOCKED_HOSTS, list)
        assert isinstance(settings.WEBHOOK_ALLOWED_HOSTS, list)

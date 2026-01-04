"""
SSRF (Server-Side Request Forgery) protection utilities for webhook delivery.

This module provides comprehensive protection against SSRF attacks by:
- Validating URLs before making HTTP requests
- Resolving hostnames to IP addresses and checking for private/internal ranges
- Blocking cloud metadata endpoints
- Preventing DNS rebinding attacks

Usage:
    from api.ssrf import validate_webhook_url, safe_request

    # Validate a URL
    validate_webhook_url("https://example.com/webhook")

    # Make a safe HTTP POST request
    response = safe_request("https://example.com/webhook", json=payload)
"""

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)


# ========================================
# Exception Classes
# ========================================


class SSRFProtectionError(Exception):
    """Base exception for SSRF protection errors."""

    pass


class BlockedHostError(SSRFProtectionError):
    """Raised when attempting to access a blocked hostname or IP."""

    pass


class PrivateIPError(SSRFProtectionError):
    """Raised when attempting to access a private/internal IP address."""

    pass


class DNSResolutionError(SSRFProtectionError):
    """Raised when DNS resolution fails or returns invalid results."""

    pass


class InvalidSchemeError(SSRFProtectionError):
    """Raised when URL scheme is not allowed (e.g., http when only https allowed)."""

    pass


# ========================================
# Private IP Range Detection
# ========================================

# Private IPv4 ranges as per RFC 1918 and others
PRIVATE_IPV4_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),  # Class A private
    ipaddress.ip_network("172.16.0.0/12"),  # Class B private
    ipaddress.ip_network("192.168.0.0/16"),  # Class C private
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS/Azure metadata)
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space (RFC 6598)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
]

# Private IPv6 ranges
PRIVATE_IPV6_RANGES = [
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("fc00::/7"),  # Unique local addresses
    ipaddress.ip_network("fe80::/10"),  # Link-local
    ipaddress.ip_network("ff00::/8"),  # Multicast
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6 addresses
]

# Cloud metadata endpoints to block
# These can be accessed by hostname or IP
BLOCKED_HOSTNAMES = [
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254",  # AWS/Azure/GCP metadata IP
    "metadata",  # Generic metadata hostname
    "localhost",  # Explicit localhost blocking
]


def is_private_ip(ip_address: str) -> bool:
    """
    Check if an IP address is private/internal.

    Args:
        ip_address: IP address string (IPv4 or IPv6)

    Returns:
        True if the IP is private/internal, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(ip_address)

        # Check IPv4 ranges
        if isinstance(ip_obj, ipaddress.IPv4Address):
            for private_range in PRIVATE_IPV4_RANGES:
                if ip_obj in private_range:
                    return True
            return False

        # Check IPv6 ranges
        if isinstance(ip_obj, ipaddress.IPv6Address):
            for private_range in PRIVATE_IPV6_RANGES:
                if ip_obj in private_range:
                    return True
            return False

        return False

    except ValueError:
        # Invalid IP address
        return True  # Treat invalid IPs as private for safety


def is_blocked_hostname(hostname: str) -> bool:
    """
    Check if a hostname is in the blocked list.

    Args:
        hostname: Hostname to check

    Returns:
        True if the hostname is blocked, False otherwise
    """
    hostname_lower = hostname.lower()

    # Check built-in blocklist
    for blocked in BLOCKED_HOSTNAMES:
        if hostname_lower == blocked.lower():
            return True

    # Check custom blocklist from settings
    custom_blocked = getattr(settings, "WEBHOOK_BLOCKED_HOSTS", [])
    for blocked in custom_blocked:
        if hostname_lower == blocked.lower():
            return True

    return False


# ========================================
# URL Validation
# ========================================


def validate_url_scheme(url: str) -> None:
    """
    Validate that the URL scheme is allowed.

    Args:
        url: URL to validate

    Raises:
        InvalidSchemeError: If the URL scheme is not allowed
    """
    parsed = urlparse(url)
    allowed_schemes = getattr(settings, "WEBHOOK_ALLOWED_SCHEMES", ["https"])

    if parsed.scheme not in allowed_schemes:
        raise InvalidSchemeError(
            f"URL scheme '{parsed.scheme}' is not allowed. "
            f"Allowed schemes: {', '.join(allowed_schemes)}"
        )


def resolve_hostname(hostname: str) -> list[str]:
    """
    Resolve a hostname to IP addresses.

    Args:
        hostname: Hostname to resolve

    Returns:
        List of IP addresses (strings)

    Raises:
        DNSResolutionError: If DNS resolution fails
    """
    try:
        # getaddrinfo returns all IP addresses for the hostname
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)

        # Extract unique IP addresses
        ip_addresses = list(set(addr[4][0] for addr in addr_info))

        if not ip_addresses:
            raise DNSResolutionError(f"DNS resolution returned no IP addresses for {hostname}")

        return ip_addresses

    except socket.gaierror as e:
        raise DNSResolutionError(f"Failed to resolve hostname '{hostname}': {e}")
    except Exception as e:
        raise DNSResolutionError(f"Unexpected error resolving hostname '{hostname}': {e}")


def validate_ip_addresses(hostname: str, ip_addresses: list[str]) -> None:
    """
    Validate that resolved IP addresses are not private/internal.

    Args:
        hostname: The hostname being validated (for error messages)
        ip_addresses: List of IP addresses to validate

    Raises:
        PrivateIPError: If any IP address is private/internal
    """
    for ip_addr in ip_addresses:
        if is_private_ip(ip_addr):
            raise PrivateIPError(
                f"Hostname '{hostname}' resolves to private IP address {ip_addr}. "
                f"Access to private/internal networks is not allowed."
            )


def validate_webhook_url(url: str) -> tuple[str, list[str]]:
    """
    Validate a webhook URL for SSRF protection.

    This function performs comprehensive SSRF validation:
    1. Check if SSRF protection is enabled (can be disabled for testing)
    2. Validate URL scheme (e.g., only https)
    3. Check if hostname is in blocklist
    4. Resolve hostname to IP addresses
    5. Check if any resolved IP is private/internal
    6. Check against allowlist (if configured)

    Args:
        url: Webhook URL to validate

    Returns:
        Tuple of (hostname, list of resolved IP addresses)

    Raises:
        InvalidSchemeError: If URL scheme is not allowed
        BlockedHostError: If hostname is in blocklist
        DNSResolutionError: If DNS resolution fails
        PrivateIPError: If hostname resolves to private/internal IP
    """
    # Check if SSRF protection is enabled
    if not getattr(settings, "WEBHOOK_SSRF_PROTECTION_ENABLED", True):
        logger.warning(
            "ssrf_protection_disabled",
            url=url,
            message="SSRF protection is disabled. This should only be used in development.",
        )
        parsed = urlparse(url)
        return (parsed.hostname or "", [])

    # Validate scheme
    validate_url_scheme(url)

    # Parse URL
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise BlockedHostError(f"Invalid URL: no hostname found in {url}")

    # Check allowlist first (if configured)
    # Allowlist bypasses all other checks - useful for testing
    allowed_hosts = getattr(settings, "WEBHOOK_ALLOWED_HOSTS", [])
    if allowed_hosts:
        hostname_lower = hostname.lower()
        if any(hostname_lower == allowed.lower() for allowed in allowed_hosts):
            logger.info(
                "ssrf_validation_allowlist_bypass",
                url=url,
                hostname=hostname,
                message="Hostname is in allowlist, bypassing SSRF checks",
            )
            return (hostname, [])

    # Check if hostname is blocked
    if is_blocked_hostname(hostname):
        raise BlockedHostError(
            f"Hostname '{hostname}' is blocked. "
            f"Access to cloud metadata endpoints and localhost is not allowed."
        )

    # Resolve hostname to IP addresses
    # This is critical for DNS rebinding protection
    ip_addresses = resolve_hostname(hostname)

    # Validate that IPs are not private/internal
    # This must be done AFTER resolution to prevent DNS rebinding attacks
    block_private_ips = getattr(settings, "WEBHOOK_BLOCK_PRIVATE_IPS", True)
    if block_private_ips:
        validate_ip_addresses(hostname, ip_addresses)

    logger.info(
        "ssrf_validation_passed",
        url=url,
        hostname=hostname,
        resolved_ips=ip_addresses,
    )

    return (hostname, ip_addresses)


# ========================================
# Safe HTTP Request Wrapper
# ========================================


def safe_request(
    url: str,
    method: str = "POST",
    json: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: Optional[int] = None,
    **kwargs,
):
    """
    Make a safe HTTP request with SSRF protection.

    This function wraps requests.request with SSRF validation. It:
    1. Validates the URL against SSRF attacks
    2. Resolves DNS and validates IP addresses
    3. Makes the request to the resolved IP with the original Host header
    4. This prevents DNS rebinding attacks (TOCTOU)

    Args:
        url: URL to request
        method: HTTP method (default: POST)
        json: JSON payload to send
        headers: HTTP headers
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to requests.request

    Returns:
        requests.Response object

    Raises:
        SSRFProtectionError: If URL validation fails
        requests.exceptions.RequestException: If HTTP request fails
    """
    import requests

    # Validate URL and get resolved IPs
    hostname, ip_addresses = validate_webhook_url(url)

    # Use configured timeout if not specified
    if timeout is None:
        timeout = getattr(settings, "WEBHOOK_REQUEST_TIMEOUT", 30)

    # If SSRF protection is disabled or allowlist is used, make direct request
    if not ip_addresses:
        logger.debug("ssrf_direct_request", url=url)
        return requests.request(
            method=method,
            url=url,
            json=json,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    # Use the first resolved IP address for the request
    # This prevents DNS rebinding attacks where the attacker's DNS server
    # returns a public IP during validation but a private IP during the request
    target_ip = ip_addresses[0]

    # Replace hostname in URL with IP address
    from urllib.parse import urlunparse

    parsed = urlparse(url)

    # Construct new URL with IP address
    # We need to preserve the port if specified
    if parsed.port:
        netloc = f"{target_ip}:{parsed.port}"
    else:
        netloc = target_ip

    request_url = urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )

    # Set Host header to original hostname (required for virtual hosting)
    if headers is None:
        headers = {}
    headers["Host"] = hostname

    logger.debug(
        "ssrf_safe_request",
        original_url=url,
        request_url=request_url,
        target_ip=target_ip,
        hostname=hostname,
    )

    # Make the request to the IP address with original Host header
    return requests.request(
        method=method,
        url=request_url,
        json=json,
        headers=headers,
        timeout=timeout,
        **kwargs,
    )

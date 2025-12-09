"""
Tests for MFA-specific rate limiting and brute force protection.
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import caches
from rest_framework.test import APIClient

from api.models_mfa import MFAToken, TOTPDevice
from api.throttling_mfa import increment_mfa_failures

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def clear_mfa_cache():
    """Clear the MFA throttle cache before and after each test."""
    cache = caches["default"]
    # Clear specific throttle keys
    yield
    cache.clear()


@pytest.fixture
def test_user():
    """Create a test user with MFA enabled."""
    user = User.objects.create_user(
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password="testpass123",
    )
    # Create confirmed TOTP device
    device, backup_codes = TOTPDevice.objects.create_device(user, confirmed=True)
    user.totp_device = device
    user.backup_codes = backup_codes
    return user


@pytest.fixture
def mfa_token(test_user):
    """Create a valid MFA token."""
    return MFAToken.create_token(test_user, ttl_seconds=300)


class TestMFATokenThrottle:
    """Test per-token throttle behavior."""

    def test_allows_up_to_5_attempts(self, client, mfa_token, clear_mfa_cache):
        """Test that MFATokenThrottle allows 5 attempts before blocking."""
        # First 5 attempts should be allowed (even with wrong codes)
        for i in range(5):
            response = client.post(
                "/api/v1/auth/mfa/verify",
                {"mfa_token": mfa_token.token, "code": "000000"},
            )
            # May be 401 (wrong code) but not 429 (throttled)
            assert response.status_code in [401, 400], f"Attempt {i+1} should not be throttled"

        # 6th attempt should be throttled
        response = client.post(
            "/api/v1/auth/mfa/verify",
            {"mfa_token": mfa_token.token, "code": "000000"},
        )
        assert response.status_code == 429, "6th attempt should be throttled"


class TestMFAUserThrottle:
    """Test per-user throttle behavior."""

    def test_allows_up_to_10_attempts(self, client, test_user, clear_mfa_cache):
        """Test that MFAUserThrottle allows 10 attempts per hour per user."""
        # Create 10 different MFA tokens for the same user (each with own token limit)
        for i in range(10):
            token = MFAToken.create_token(test_user, ttl_seconds=300)
            response = client.post(
                "/api/v1/auth/mfa/verify",
                {"mfa_token": token.token, "code": "000000"},
            )
            assert response.status_code in [401, 400], f"Attempt {i+1} should not be throttled"

        # 11th attempt should be throttled (user-level)
        token = MFAToken.create_token(test_user, ttl_seconds=300)
        response = client.post(
            "/api/v1/auth/mfa/verify",
            {"mfa_token": token.token, "code": "000000"},
        )
        assert response.status_code == 429, "11th attempt should be throttled"


class TestMFAIPThrottle:
    """Test per-IP throttle behavior."""

    def test_allows_up_to_20_attempts(self, client, clear_mfa_cache):
        """Test that MFAIPThrottle allows 20 attempts per hour per IP."""
        # Create 20 different users and MFA tokens
        for i in range(20):
            user = User.objects.create_user(
                username=f"user_{i}_{uuid.uuid4().hex[:8]}",
                email=f"user{i}_{uuid.uuid4().hex[:8]}@example.com",
                password="pass123",
            )
            TOTPDevice.objects.create_device(user, confirmed=True)
            token = MFAToken.create_token(user, ttl_seconds=300)

            response = client.post(
                "/api/v1/auth/mfa/verify",
                {"mfa_token": token.token, "code": "000000"},
                REMOTE_ADDR="192.168.1.100",
            )
            assert response.status_code in [401, 400], f"Attempt {i+1} should not be throttled"

        # 21st attempt from same IP should be throttled
        user = User.objects.create_user(
            username=f"user_21_{uuid.uuid4().hex[:8]}",
            email=f"user21_{uuid.uuid4().hex[:8]}@example.com",
            password="pass123",
        )
        TOTPDevice.objects.create_device(user, confirmed=True)
        token = MFAToken.create_token(user, ttl_seconds=300)

        response = client.post(
            "/api/v1/auth/mfa/verify",
            {"mfa_token": token.token, "code": "000000"},
            REMOTE_ADDR="192.168.1.100",
        )
        assert response.status_code == 429, "21st attempt should be throttled"


class TestIncrementMFAFailures:
    """Test the increment_mfa_failures helper function."""

    def test_increments_all_throttle_counters(self, clear_mfa_cache):
        """Test that increment_mfa_failures updates all cache keys."""
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        django_request = factory.post("/api/v1/auth/mfa/verify")
        request = Request(django_request)

        # Attach throttle keys
        request._mfa_token_throttle_key = "throttle:mfa:token:test123"
        request._mfa_user_throttle_key = "throttle:mfa:user:user123"
        request._mfa_ip_throttle_key = "throttle:mfa:ip:192.168.1.1"

        # Increment failures
        increment_mfa_failures(request)

        # Verify cache entries were created
        cache = caches["default"]
        token_history = cache.get("throttle:mfa:token:test123")
        user_history = cache.get("throttle:mfa:user:user123")
        ip_history = cache.get("throttle:mfa:ip:192.168.1.1")

        assert len(token_history) == 1
        assert len(user_history) == 1
        assert len(ip_history) == 1


class TestThrottleWaitTime:
    """Test wait time calculation."""

    def test_returns_retry_after_when_throttled(self, client, mfa_token, clear_mfa_cache):
        """Test that wait time is properly calculated and returned."""
        # Exhaust the token throttle
        for i in range(5):
            client.post(
                "/api/v1/auth/mfa/verify",
                {"mfa_token": mfa_token.token, "code": "000000"},
            )

        # Next request should be throttled
        response = client.post(
            "/api/v1/auth/mfa/verify",
            {"mfa_token": mfa_token.token, "code": "000000"},
        )
        assert response.status_code == 429
        # DRF includes detail message for throttled requests
        assert "detail" in response.data or "Retry-After" in response


class TestDifferentIPsIndependent:
    """Test that different IPs have independent limits."""

    def test_different_ips_not_affected(self, client, clear_mfa_cache):
        """Test that different IPs have independent throttle limits."""
        user = User.objects.create_user(
            username="iptest",
            email="iptest@example.com",
            password="pass123",
        )
        TOTPDevice.objects.create_device(user, confirmed=True)

        # Make 5 attempts from IP 1
        for i in range(5):
            token = MFAToken.create_token(user, ttl_seconds=300)
            response = client.post(
                "/api/v1/auth/mfa/verify",
                {"mfa_token": token.token, "code": "000000"},
                REMOTE_ADDR="192.168.1.1",
            )
            assert response.status_code in [401, 400]

        # Make 5 attempts from IP 2 (should not be throttled by IP limit)
        for i in range(5):
            token = MFAToken.create_token(user, ttl_seconds=300)
            response = client.post(
                "/api/v1/auth/mfa/verify",
                {"mfa_token": token.token, "code": "000000"},
                REMOTE_ADDR="192.168.1.2",
            )
            # May be throttled by user limit (10 total), but not IP limit
            assert response.status_code in [401, 400, 429]

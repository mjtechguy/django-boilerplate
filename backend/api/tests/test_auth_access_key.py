"""
Tests for Access Key HMAC authentication.

Tests cover:
- Valid signature authentication
- Expired/future timestamp rejection
- Invalid signature rejection
- Missing/malformed headers
- Revoked access keys
"""

import time
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from api.auth_access_key import (
    AccessKeyAuthentication,
    compute_signature,
)
from api.models_access_keys import AccessKeyPair

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password="testpass123",
    )


@pytest.fixture
def access_key(user):
    """Create an access key pair for the user."""
    key_pair, _ = AccessKeyPair.objects.create_key_pair(user, name="Test Key")
    return key_pair


@pytest.fixture
def factory():
    """Create an API request factory."""
    return APIRequestFactory()


@pytest.fixture
def authenticator():
    """Create an AccessKeyAuthentication instance."""
    return AccessKeyAuthentication()


class TestAccessKeyAuthentication:
    """Test the AccessKeyAuthentication class."""

    def test_no_auth_header_returns_none(self, factory, authenticator):
        """Test that missing auth header returns None (allows other auth methods)."""
        request = factory.get("/api/v1/test")
        result = authenticator.authenticate(request)
        assert result is None

    def test_wrong_auth_scheme_returns_none(self, factory, authenticator):
        """Test that wrong auth scheme returns None."""
        request = factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer token123")
        result = authenticator.authenticate(request)
        assert result is None

    def test_valid_authentication_succeeds(self, factory, authenticator, access_key):
        """Test that valid AKSK authentication succeeds."""
        timestamp = str(int(time.time()))
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        result = authenticator.authenticate(request)
        assert result is not None
        user, auth_key = result
        assert user.id == access_key.user.id
        assert auth_key.id == access_key.id

    def test_invalid_signature_fails(self, factory, authenticator, access_key):
        """Test that invalid signature raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        timestamp = str(int(time.time()))
        path = "/api/v1/test"

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature=invalidsignature"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "Invalid signature" in str(exc_info.value)

    def test_expired_timestamp_fails(self, factory, authenticator, access_key):
        """Test that expired timestamp (too old) raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        # 10 minutes ago (beyond 5 minute tolerance)
        timestamp = str(int(time.time()) - 600)
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "expired" in str(exc_info.value).lower()

    def test_future_timestamp_fails(self, factory, authenticator, access_key):
        """Test that future timestamp (too far ahead) raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        # 10 minutes in the future
        timestamp = str(int(time.time()) + 600)
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "expired" in str(exc_info.value).lower()

    def test_invalid_timestamp_format_fails(self, factory, authenticator, access_key):
        """Test that invalid timestamp format raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        path = "/api/v1/test"
        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp=not-a-number, Signature=abc123"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "timestamp" in str(exc_info.value).lower()

    def test_revoked_key_fails(self, factory, authenticator, access_key):
        """Test that revoked access key raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        # Revoke the key
        access_key.revoke()

        timestamp = str(int(time.time()))
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "Invalid access key" in str(exc_info.value)

    def test_nonexistent_key_fails(self, factory, authenticator):
        """Test that non-existent access key raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        timestamp = str(int(time.time()))
        path = "/api/v1/test"

        auth_header = f"AKSK AccessKeyId=AKnonexistent12345, Timestamp={timestamp}, Signature=abc123"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "Invalid access key" in str(exc_info.value)

    def test_missing_access_key_id_fails(self, factory, authenticator):
        """Test that missing AccessKeyId raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        timestamp = str(int(time.time()))
        path = "/api/v1/test"

        auth_header = f"AKSK Timestamp={timestamp}, Signature=abc123"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "AccessKeyId" in str(exc_info.value)

    def test_missing_timestamp_fails(self, factory, authenticator, access_key):
        """Test that missing Timestamp raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        path = "/api/v1/test"
        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Signature=abc123"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "Timestamp" in str(exc_info.value)

    def test_missing_signature_fails(self, factory, authenticator, access_key):
        """Test that missing Signature raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        timestamp = str(int(time.time()))
        path = "/api/v1/test"

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed) as exc_info:
            authenticator.authenticate(request)
        assert "Signature" in str(exc_info.value)

    def test_malformed_header_fails(self, factory, authenticator):
        """Test that malformed header raises AuthenticationFailed."""
        from rest_framework.exceptions import AuthenticationFailed

        path = "/api/v1/test"
        auth_header = "AKSK this-is-not-valid"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        with pytest.raises(AuthenticationFailed):
            authenticator.authenticate(request)

    def test_last_used_timestamp_updated(self, factory, authenticator, access_key):
        """Test that last_used_at is updated on successful auth."""
        original_last_used = access_key.last_used_at

        timestamp = str(int(time.time()))
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        authenticator.authenticate(request)

        # Refresh from database
        access_key.refresh_from_db()
        assert access_key.last_used_at is not None
        if original_last_used:
            assert access_key.last_used_at > original_last_used

    def test_authenticate_header_method(self, factory, authenticator):
        """Test that authenticate_header returns the correct keyword."""
        request = factory.get("/api/v1/test")
        assert authenticator.authenticate_header(request) == "AKSK"


class TestSignatureComputation:
    """Test the compute_signature function."""

    def test_signature_is_deterministic(self, access_key):
        """Test that same inputs produce same signature."""
        sig1 = compute_signature("secret", "12345", "GET", "/path")
        sig2 = compute_signature("secret", "12345", "GET", "/path")
        assert sig1 == sig2

    def test_different_secrets_produce_different_signatures(self):
        """Test that different secrets produce different signatures."""
        sig1 = compute_signature("secret1", "12345", "GET", "/path")
        sig2 = compute_signature("secret2", "12345", "GET", "/path")
        assert sig1 != sig2

    def test_different_timestamps_produce_different_signatures(self):
        """Test that different timestamps produce different signatures."""
        sig1 = compute_signature("secret", "12345", "GET", "/path")
        sig2 = compute_signature("secret", "12346", "GET", "/path")
        assert sig1 != sig2

    def test_different_methods_produce_different_signatures(self):
        """Test that different HTTP methods produce different signatures."""
        sig1 = compute_signature("secret", "12345", "GET", "/path")
        sig2 = compute_signature("secret", "12345", "POST", "/path")
        assert sig1 != sig2

    def test_different_paths_produce_different_signatures(self):
        """Test that different paths produce different signatures."""
        sig1 = compute_signature("secret", "12345", "GET", "/path1")
        sig2 = compute_signature("secret", "12345", "GET", "/path2")
        assert sig1 != sig2

    def test_signature_is_hex_sha256(self):
        """Test that signature is a valid hex SHA256 hash."""
        sig = compute_signature("secret", "12345", "GET", "/path")
        # SHA256 produces 64 hex characters
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_method_is_uppercased(self):
        """Test that method is uppercased in signature."""
        sig_lower = compute_signature("secret", "12345", "get", "/path")
        sig_upper = compute_signature("secret", "12345", "GET", "/path")
        assert sig_lower == sig_upper


class TestTimestampTolerance:
    """Test timestamp tolerance settings."""

    def test_timestamp_within_tolerance_succeeds(self, factory, authenticator, access_key):
        """Test that timestamp within 5 minutes succeeds."""
        # 4 minutes ago (within tolerance)
        timestamp = str(int(time.time()) - 240)
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        result = authenticator.authenticate(request)
        assert result is not None

    def test_timestamp_at_boundary_succeeds(self, factory, authenticator, access_key):
        """Test that timestamp exactly at 5 minute boundary succeeds."""
        # Exactly 5 minutes ago (at tolerance boundary)
        timestamp = str(int(time.time()) - 299)  # Just under 300 seconds
        method = "GET"
        path = "/api/v1/test"

        signature = compute_signature(
            secret=access_key.secret_access_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        auth_header = f"AKSK AccessKeyId={access_key.access_key_id}, Timestamp={timestamp}, Signature={signature}"
        request = factory.get(path, HTTP_AUTHORIZATION=auth_header)

        result = authenticator.authenticate(request)
        assert result is not None

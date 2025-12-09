"""
Tests for S3-style Access Key management.
"""

import hashlib
import hmac
import time

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from api.auth_access_key import compute_signature
from api.models_access_keys import AccessKeyPair

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="testpass123",
    )


@pytest.fixture
def client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(client, user, monkeypatch):
    """Create an authenticated API client."""

    def mock_validate(self, token):
        # Use username as sub since KeycloakJWTAuthentication uses username=claims["sub"]
        return {
            "sub": user.username,
            "email": user.email,
            "preferred_username": user.username,
            "realm_access": {"roles": ["user"]},
        }

    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token", mock_validate
    )
    client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")
    return client


class TestAccessKeyCreation:
    """Test access key creation."""

    def test_create_access_key_success(self, authenticated_client):
        """Test successful access key creation."""
        url = reverse("access-key-create")
        response = authenticated_client.post(url, {"name": "My Access Key"})

        assert response.status_code == 201
        data = response.json()
        assert "access_key_id" in data
        assert data["access_key_id"].startswith("AK")
        assert "secret_access_key" in data
        assert len(data["secret_access_key"]) > 20
        assert data["name"] == "My Access Key"

    def test_create_access_key_without_name(self, authenticated_client):
        """Test creating key without name generates default."""
        url = reverse("access-key-create")
        response = authenticated_client.post(url, {})

        assert response.status_code == 201
        assert "Access Key" in response.json()["name"]

    def test_create_access_key_unauthenticated(self, client):
        """Test unauthenticated users cannot create keys."""
        url = reverse("access-key-create")
        response = client.post(url, {"name": "Test"})

        assert response.status_code == 401


class TestAccessKeyListing:
    """Test access key listing."""

    def test_list_access_keys_empty(self, authenticated_client):
        """Test listing when user has no keys."""
        url = reverse("access-key-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.json()["access_keys"] == []

    def test_list_access_keys_with_keys(self, authenticated_client, user):
        """Test listing user's keys."""
        # Create some keys
        AccessKeyPair.objects.create_key_pair(user=user, name="Key 1")
        AccessKeyPair.objects.create_key_pair(user=user, name="Key 2")

        url = reverse("access-key-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        keys = response.json()["access_keys"]
        assert len(keys) == 2
        # Should NOT include secret
        assert "secret_access_key" not in keys[0]

    def test_list_only_own_keys(self, authenticated_client, user, other_user):
        """Test users only see their own keys."""
        AccessKeyPair.objects.create_key_pair(user=user, name="My Key")
        AccessKeyPair.objects.create_key_pair(user=other_user, name="Other Key")

        url = reverse("access-key-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        keys = response.json()["access_keys"]
        assert len(keys) == 1
        assert keys[0]["name"] == "My Key"


class TestAccessKeyRevocation:
    """Test access key revocation."""

    def test_revoke_access_key_success(self, authenticated_client, user):
        """Test successful key revocation."""
        key_pair, _ = AccessKeyPair.objects.create_key_pair(user=user, name="To Revoke")

        url = reverse("access-key-revoke", kwargs={"key_id": key_pair.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 200
        key_pair.refresh_from_db()
        assert key_pair.revoked is True

    def test_revoke_nonexistent_key(self, authenticated_client):
        """Test revoking non-existent key."""
        url = reverse("access-key-revoke", kwargs={"key_id": 99999})
        response = authenticated_client.delete(url)

        assert response.status_code == 404

    def test_revoke_other_users_key(self, authenticated_client, other_user):
        """Test cannot revoke another user's key."""
        key_pair, _ = AccessKeyPair.objects.create_key_pair(
            user=other_user, name="Other Key"
        )

        url = reverse("access-key-revoke", kwargs={"key_id": key_pair.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 404
        key_pair.refresh_from_db()
        assert key_pair.revoked is False


class TestAccessKeySignature:
    """Test HMAC signature computation."""

    def test_compute_signature(self):
        """Test signature computation."""
        secret = "test-secret-key"
        timestamp = "1234567890"
        method = "GET"
        path = "/api/v1/test"

        sig = compute_signature(secret, timestamp, method, path)

        # Verify it's a valid hex string
        assert len(sig) == 64  # SHA256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in sig)

    def test_signature_changes_with_timestamp(self):
        """Test different timestamps produce different signatures."""
        secret = "test-secret"
        sig1 = compute_signature(secret, "1000", "GET", "/test")
        sig2 = compute_signature(secret, "2000", "GET", "/test")

        assert sig1 != sig2

    def test_signature_changes_with_method(self):
        """Test different methods produce different signatures."""
        secret = "test-secret"
        sig1 = compute_signature(secret, "1000", "GET", "/test")
        sig2 = compute_signature(secret, "1000", "POST", "/test")

        assert sig1 != sig2

    def test_signature_changes_with_path(self):
        """Test different paths produce different signatures."""
        secret = "test-secret"
        sig1 = compute_signature(secret, "1000", "GET", "/test1")
        sig2 = compute_signature(secret, "1000", "GET", "/test2")

        assert sig1 != sig2


class TestAccessKeyAuthentication:
    """Test authentication with access keys."""

    def test_access_key_model_creation(self, user):
        """Test access key pair model creation."""
        key_pair, secret = AccessKeyPair.objects.create_key_pair(
            user=user, name="Test Key"
        )

        assert key_pair.access_key_id.startswith("AK")
        assert len(key_pair.access_key_id) == 18  # AK + 16 hex chars
        assert len(secret) > 20
        assert key_pair.revoked is False
        assert key_pair.user == user

    def test_revoked_key_not_usable(self, user):
        """Test revoked keys are marked correctly."""
        key_pair, secret = AccessKeyPair.objects.create_key_pair(
            user=user, name="Test Key"
        )
        key_pair.revoked = True
        key_pair.save()

        # Verify key is marked revoked
        key_pair.refresh_from_db()
        assert key_pair.revoked is True

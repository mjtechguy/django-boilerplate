"""
Tests for user impersonation functionality.

Tests cover:
- Impersonation is disabled by default
- Only platform_admin can impersonate
- Impersonation header handling
- Impersonation logging
- API endpoint for impersonation logs
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from api.impersonation import can_impersonate, get_impersonated_user, log_impersonation
from api.models import ImpersonationLog

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_auth_cache(monkeypatch):
    """Clear JWKS cache before each test."""
    from api import auth

    auth._jwks_cache.cache_clear()  # noqa: SLF001
    yield


@pytest.fixture
def client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def mock_platform_admin_auth(monkeypatch):
    """Patch KeycloakJWTAuthentication to return platform_admin user."""

    def _mock_validate(self, token):
        return {
            "sub": "admin-123",
            "email": "admin@example.com",
            "realm_roles": ["platform_admin"],
            "client_roles": [],
        }

    monkeypatch.setattr("api.auth.KeycloakJWTAuthentication._validate_token", _mock_validate)
    return _mock_validate


@pytest.fixture
def mock_regular_user_auth(monkeypatch):
    """Patch KeycloakJWTAuthentication to return regular user."""

    def _mock_validate(self, token):
        return {
            "sub": "user-456",
            "email": "user@example.com",
            "realm_roles": ["user"],
            "client_roles": ["org_admin"],
        }

    monkeypatch.setattr("api.auth.KeycloakJWTAuthentication._validate_token", _mock_validate)
    return _mock_validate


class TestImpersonationHelpers:
    """Tests for impersonation helper functions."""

    def test_can_impersonate_with_platform_admin_realm_role(self):
        """Test that platform_admin realm role allows impersonation."""
        claims = {
            "sub": "admin-123",
            "realm_roles": ["platform_admin"],
            "client_roles": [],
        }
        assert can_impersonate(claims) is True

    def test_can_impersonate_with_platform_admin_client_role(self):
        """Test that platform_admin client role allows impersonation."""
        claims = {
            "sub": "admin-123",
            "realm_roles": [],
            "client_roles": ["platform_admin"],
        }
        assert can_impersonate(claims) is True

    def test_cannot_impersonate_without_platform_admin(self):
        """Test that users without platform_admin cannot impersonate."""
        claims = {
            "sub": "user-456",
            "realm_roles": ["user"],
            "client_roles": ["org_admin"],
        }
        assert can_impersonate(claims) is False

    def test_get_impersonated_user_creates_new_user(self):
        """Test that get_impersonated_user creates a new user if needed."""
        user = get_impersonated_user("new-user-123")
        assert user is not None
        assert user.username == "new-user-123"

    def test_get_impersonated_user_returns_existing_user(self):
        """Test that get_impersonated_user returns existing user."""
        # Create user first
        user1 = get_impersonated_user("existing-user-123")
        # Get same user
        user2 = get_impersonated_user("existing-user-123")
        assert user1.id == user2.id

    def test_log_impersonation_creates_log_entry(self):
        """Test that log_impersonation creates a log entry."""
        log = log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-456",
            target_user_email="user@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
            org_id="org-789",
            request_id="req-abc",
            metadata={"ip": "192.168.1.1"},
        )

        assert log.admin_id == "admin-123"
        assert log.admin_email == "admin@example.com"
        assert log.target_user_id == "user-456"
        assert log.target_user_email == "user@example.com"
        assert log.action == "start"
        assert log.endpoint == "/api/v1/ping"
        assert log.method == "GET"
        assert log.org_id == "org-789"
        assert log.request_id == "req-abc"
        assert log.metadata == {"ip": "192.168.1.1"}


class TestImpersonationDisabledByDefault:
    """Tests that impersonation is disabled by default."""

    def test_impersonation_disabled_by_default(self, client, mock_platform_admin_auth, settings):
        """Test that impersonation is disabled by default."""
        settings.IMPERSONATION_ENABLED = False

        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
            HTTP_X_IMPERSONATE_USER="target-user-123",
        )

        # Should fail with authentication error
        assert resp.status_code == 401
        assert "not enabled" in resp.json()["detail"].lower()


class TestImpersonationAuthentication:
    """Tests for impersonation during authentication."""

    def test_platform_admin_can_impersonate(
        self, client, mock_platform_admin_auth, settings, django_user_model
    ):
        """Test that platform_admin can impersonate users."""
        settings.IMPERSONATION_ENABLED = True

        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
            HTTP_X_IMPERSONATE_USER="target-user-123",
        )

        assert resp.status_code == 200
        # The user returned should be the impersonated user
        data = resp.json()
        assert data["user"] == "target-user-123"
        assert data["claims_sub"] == "admin-123"  # Original admin claims preserved

    def test_regular_user_cannot_impersonate(self, client, mock_regular_user_auth, settings):
        """Test that regular users cannot impersonate."""
        settings.IMPERSONATION_ENABLED = True

        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
            HTTP_X_IMPERSONATE_USER="target-user-123",
        )

        # Should fail with permission error
        assert resp.status_code == 401
        assert "permission" in resp.json()["detail"].lower()

    def test_impersonation_creates_log_entry(self, client, mock_platform_admin_auth, settings):
        """Test that impersonation creates a log entry."""
        settings.IMPERSONATION_ENABLED = True

        # Clear existing logs
        ImpersonationLog.objects.all().delete()

        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
            HTTP_X_IMPERSONATE_USER="target-user-123",
        )

        assert resp.status_code == 200

        # Check that a log entry was created
        logs = ImpersonationLog.objects.all()
        assert logs.count() == 1

        log = logs.first()
        assert log.admin_id == "admin-123"
        assert log.admin_email == "admin@example.com"
        assert log.target_user_id == "target-user-123"
        assert log.action == "start"
        assert log.endpoint == "/api/v1/ping"
        assert log.method == "GET"

    def test_no_impersonation_without_header(self, client, mock_platform_admin_auth, settings):
        """Test that normal authentication works without impersonation header."""
        settings.IMPERSONATION_ENABLED = True

        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        data = resp.json()
        # User should be the admin themselves
        assert data["user"] == "admin-123"
        assert data["claims_sub"] == "admin-123"


class TestImpersonationLogAPI:
    """Tests for the impersonation log API endpoint."""

    def test_list_impersonation_logs(self, client, mock_platform_admin_auth):
        """Test listing impersonation logs."""
        # Create some logs
        log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-1",
            target_user_email="user1@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
        )
        log_impersonation(
            admin_id="admin-456",
            admin_email="admin2@example.com",
            target_user_id="user-2",
            target_user_email="user2@example.com",
            action="start",
            endpoint="/api/v1/protected",
            method="POST",
        )

        resp = client.get(
            reverse("impersonation-logs"),
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        assert resp.data["count"] >= 2
        assert len(resp.data["results"]) >= 2

    def test_filter_by_admin_id(self, client, mock_platform_admin_auth):
        """Test filtering logs by admin_id."""
        ImpersonationLog.objects.all().delete()

        log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-1",
            target_user_email="user1@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
        )
        log_impersonation(
            admin_id="admin-456",
            admin_email="admin2@example.com",
            target_user_id="user-2",
            target_user_email="user2@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
        )

        resp = client.get(
            reverse("impersonation-logs") + "?admin_id=admin-123",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        assert all(log["admin_id"] == "admin-123" for log in resp.data["results"])

    def test_filter_by_target_user_id(self, client, mock_platform_admin_auth):
        """Test filtering logs by target_user_id."""
        ImpersonationLog.objects.all().delete()

        log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-1",
            target_user_email="user1@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
        )
        log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-2",
            target_user_email="user2@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
        )

        resp = client.get(
            reverse("impersonation-logs") + "?target_user_id=user-1",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        assert all(log["target_user_id"] == "user-1" for log in resp.data["results"])

    def test_filter_by_action(self, client, mock_platform_admin_auth):
        """Test filtering logs by action."""
        ImpersonationLog.objects.all().delete()

        log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-1",
            target_user_email="user1@example.com",
            action="start",
            endpoint="/api/v1/ping",
            method="GET",
        )
        log_impersonation(
            admin_id="admin-123",
            admin_email="admin@example.com",
            target_user_id="user-1",
            target_user_email="user1@example.com",
            action="end",
            endpoint="/api/v1/ping",
            method="GET",
        )

        resp = client.get(
            reverse("impersonation-logs") + "?action=start",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        assert all(log["action"] == "start" for log in resp.data["results"])

    def test_non_platform_admin_cannot_access_logs(self, client, mock_regular_user_auth):
        """Test that non-platform_admin cannot access impersonation logs."""
        resp = client.get(
            reverse("impersonation-logs"),
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 403

    def test_pagination(self, client, mock_platform_admin_auth):
        """Test pagination of impersonation logs."""
        ImpersonationLog.objects.all().delete()

        # Create 25 logs
        for i in range(25):
            log_impersonation(
                admin_id="admin-123",
                admin_email="admin@example.com",
                target_user_id=f"user-{i}",
                target_user_email=f"user{i}@example.com",
                action="start",
                endpoint="/api/v1/ping",
                method="GET",
            )

        # Get first page
        resp = client.get(
            reverse("impersonation-logs") + "?limit=10&offset=0",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        assert len(resp.data["results"]) == 10
        assert resp.data["count"] == 25
        assert resp.data["limit"] == 10
        assert resp.data["offset"] == 0

        # Get second page
        resp = client.get(
            reverse("impersonation-logs") + "?limit=10&offset=10",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        assert len(resp.data["results"]) == 10
        assert resp.data["offset"] == 10


class TestImpersonationMetadata:
    """Tests for impersonation metadata on request object."""

    def test_impersonation_metadata_set_when_impersonating(
        self, client, mock_platform_admin_auth, settings
    ):
        """Test that impersonation metadata is set on request when impersonating."""
        settings.IMPERSONATION_ENABLED = True

        # We can't directly access request object in tests, but we can verify
        # the behavior through the authentication flow
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
            HTTP_X_IMPERSONATE_USER="target-user-123",
        )

        assert resp.status_code == 200
        # Verify the impersonation happened
        assert resp.json()["user"] == "target-user-123"

    def test_impersonation_metadata_not_impersonating(
        self, client, mock_platform_admin_auth, settings
    ):
        """Test that impersonation metadata indicates not impersonating when no header."""
        settings.IMPERSONATION_ENABLED = True

        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        assert resp.status_code == 200
        # No impersonation - user should be the admin
        assert resp.json()["user"] == "admin-123"

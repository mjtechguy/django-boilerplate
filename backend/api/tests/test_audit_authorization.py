"""
Tests for audit log authorization and security.

Tests cover:
- Unauthenticated access is denied
- Regular users cannot access audit logs
- Org admins can only see their organization's logs
- Platform admins can see all logs
- Audit viewer role works correctly
- Export endpoint requires MFA
- Verify endpoint requires platform_admin
- Access to audit logs is itself logged (meta-audit)
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from api.models import AuditLog, Org

User = get_user_model()

pytestmark = pytest.mark.django_db


def create_mock_token_claims(
    user_id="test-user",
    email="test@example.com",
    roles=None,
    org_id=None,
    mfa_level=0,
):
    """Helper to create mock token claims."""
    if roles is None:
        roles = []

    return {
        "sub": user_id,
        "email": email,
        "realm_roles": roles,
        "client_roles": [],
        "roles": [],
        "org_id": org_id,
        "mfa_level": mfa_level,
        "team_ids": [],
        "license_tier": "free",
        "risk_flags": [],
    }


class TestAuditLogListAuthorization:
    """Tests for audit log list endpoint authorization."""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        client = APIClient()
        response = client.get("/api/v1/audit")

        assert response.status_code == 401

    @patch("api.auth.KeycloakJWTAuthentication.authenticate")
    def test_regular_user_access_denied(self, mock_auth):
        """Test that regular users without audit permissions are denied."""
        user = User.objects.create(username="regular-user", email="regular@example.com")
        claims = create_mock_token_claims(
            user_id="regular-user",
            email="regular@example.com",
            roles=["user"],  # No audit permissions
            org_id="org-123",
        )

        mock_auth.return_value = (user, "mock-token")

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        # Mock the token_claims attribute on the request
        with patch("api.permissions.getattr") as mock_getattr:
            mock_getattr.return_value = claims
            response = client.get("/api/v1/audit")

        assert response.status_code == 403
        assert "permission" in response.data.get("detail", "").lower()

    def test_org_admin_sees_only_their_org_logs(self):
        """Test that org admins can only see their organization's logs."""
        # Clear any existing audit logs
        AuditLog.objects.all().delete()

        # Create test data (Org creation triggers audit log via signals)
        org1 = Org.objects.create(name="Org 1")
        org2 = Org.objects.create(name="Org 2")

        # Create additional audit logs for different orgs
        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id=str(org1.id),
            actor_id="user-1",
            org_id=str(org1.id),
        )
        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id=str(org2.id),
            actor_id="user-2",
            org_id=str(org2.id),
        )

        # Create user with org_admin role for org1
        claims = create_mock_token_claims(
            user_id="org-admin",
            email="admin@org1.com",
            roles=["org_admin"],
            org_id=str(org1.id),
        )

        # Test the queryset filtering logic directly
        from api.views_audit import AuditLogListView

        view = AuditLogListView()

        # Mock the request with token_claims
        class MockRequest:
            token_claims = claims

        view.request = MockRequest()

        queryset = view.get_queryset()

        # Should only return logs for org1 (signal log + manual log = 2)
        assert queryset.filter(org_id=str(org1.id)).count() == 2
        assert queryset.filter(org_id=str(org2.id)).count() == 0

    def test_platform_admin_sees_all_logs(self):
        """Test that platform admins can see all audit logs."""
        # Clear any existing audit logs
        AuditLog.objects.all().delete()

        # Create test data (Org creation triggers audit log via signals)
        org1 = Org.objects.create(name="Org 1")
        org2 = Org.objects.create(name="Org 2")

        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id=str(org1.id),
            actor_id="user-1",
            org_id=str(org1.id),
        )
        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id=str(org2.id),
            actor_id="user-2",
            org_id=str(org2.id),
        )

        # Create platform admin claims
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
            org_id=None,
        )

        from api.views_audit import AuditLogListView

        view = AuditLogListView()

        class MockRequest:
            token_claims = claims

        view.request = MockRequest()

        queryset = view.get_queryset()

        # Should return all logs (signal logs + manual logs = 4 total)
        assert queryset.count() == 4
        assert queryset.filter(org_id=str(org1.id)).count() == 2
        assert queryset.filter(org_id=str(org2.id)).count() == 2

    def test_audit_viewer_role_works(self):
        """Test that audit_viewer role can access logs."""
        # Clear any existing audit logs
        AuditLog.objects.all().delete()

        org = Org.objects.create(name="Test Org")

        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id=str(org.id),
            actor_id="user-1",
            org_id=str(org.id),
        )

        claims = create_mock_token_claims(
            user_id="auditor",
            email="auditor@org.com",
            roles=["audit_viewer"],
            org_id=str(org.id),
        )

        from api.views_audit import AuditLogListView

        view = AuditLogListView()

        class MockRequest:
            token_claims = claims

        view.request = MockRequest()

        queryset = view.get_queryset()

        # Should see their org's logs (signal log + manual log = 2)
        assert queryset.filter(org_id=str(org.id)).count() == 2

    def test_user_without_org_context_has_no_access(self):
        """Test that users without org context cannot see any logs."""
        from api.views_audit import AuditLogListView

        view = AuditLogListView()

        class MockRequest:
            token_claims = create_mock_token_claims(
                user_id="user",
                email="user@example.com",
                roles=["org_admin"],
                org_id=None,  # No org context
            )

        view.request = MockRequest()

        queryset = view.get_queryset()

        # Should return empty queryset
        assert queryset.count() == 0


class TestAuditLogExportAuthorization:
    """Tests for audit log export endpoint authorization."""

    def test_export_requires_platform_admin(self):
        """Test that export endpoint requires platform_admin role."""
        user = User.objects.create(username="org-admin", email="admin@org.com")
        claims = create_mock_token_claims(
            user_id="org-admin",
            email="admin@org.com",
            roles=["org_admin"],  # Not platform_admin
            org_id="org-123",
            mfa_level=1,
        )

        from api.permissions import IsPlatformAdmin

        perm = IsPlatformAdmin()

        # Use a simple object with attributes instead of a nested class
        request = type("MockRequest", (), {"user": user, "token_claims": claims})()

        # Should deny access
        assert not perm.has_permission(request, None)

    @patch("api.views_audit.logger")
    def test_export_requires_mfa(self, mock_logger):
        """Test that export endpoint requires MFA verification."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
            mfa_level=0,  # No MFA
        )

        from api.views_audit import AuditLogExportView

        view = AuditLogExportView()

        # Use type() to create a simple mock request
        request = type(
            "MockRequest", (), {"user": user, "token_claims": claims, "query_params": {}}
        )()

        response = view.get(request)

        # Should deny access without MFA
        assert response.status_code == 403
        assert "MFA required" in response.data["error"]

    @patch("api.views_audit.logger")
    def test_export_works_with_mfa(self, mock_logger):
        """Test that export works with platform_admin + MFA."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
            mfa_level=1,  # MFA verified
        )

        # Create some test data
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="123",
            actor_id="user-1",
        )

        from api.views_audit import AuditLogExportView

        view = AuditLogExportView()

        request = type(
            "MockRequest", (), {"user": user, "token_claims": claims, "query_params": {}}
        )()

        response = view.get(request)

        # Should allow access
        assert response.status_code == 200
        assert "results" in response.data
        assert response.data["count"] >= 1


class TestAuditLogVerifyAuthorization:
    """Tests for audit log verification endpoint authorization."""

    def test_verify_requires_platform_admin(self):
        """Test that verify endpoint requires platform_admin role."""
        user = User.objects.create(username="org-admin", email="admin@org.com")
        claims = create_mock_token_claims(
            user_id="org-admin",
            email="admin@org.com",
            roles=["org_admin"],  # Not platform_admin
        )

        from api.permissions import IsPlatformAdmin

        perm = IsPlatformAdmin()

        request = type("MockRequest", (), {"user": user, "token_claims": claims})()

        # Should deny access
        assert not perm.has_permission(request, None)

    @patch("api.views_audit.logger")
    def test_verify_works_for_platform_admin(self, mock_logger):
        """Test that verify works for platform admins."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
        )

        # Create some test data
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="123",
            actor_id="user-1",
        )

        from api.views_audit import AuditLogVerifyView

        view = AuditLogVerifyView()

        request = type("MockRequest", (), {"user": user, "token_claims": claims})()

        response = view.get(request)

        # Should allow access
        assert response.status_code == 200
        assert response.data["status"] == "verified"
        assert response.data["total_logs"] >= 1


class TestAuditAccessLogging:
    """Tests for meta-audit logging (logging access to audit logs)."""

    @patch("api.views_audit.logger")
    def test_audit_log_access_is_logged(self, mock_logger):
        """Test that accessing audit logs is itself logged."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
            org_id="org-123",
        )

        from api.views_audit import AuditLogListView

        view = AuditLogListView()

        request = type(
            "MockRequest",
            (),
            {
                "user": user,
                "token_claims": claims,
                "query_params": {"org_id": "org-123", "action": "create"},
            },
        )()

        # Set request on view before calling get()
        view.request = request

        view.get(request)

        # Verify that logger.info was called with audit access event
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "audit_log_accessed"
        assert call_args[1]["actor_id"] == "platform-admin"
        assert call_args[1]["org_id"] == "org-123"
        assert "query_params" in call_args[1]

    @patch("api.views_audit.logger")
    def test_audit_export_is_logged(self, mock_logger):
        """Test that exporting audit logs is logged."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
            mfa_level=1,
        )

        from api.views_audit import AuditLogExportView

        view = AuditLogExportView()

        request = type(
            "MockRequest", (), {"user": user, "token_claims": claims, "query_params": {}}
        )()

        view.get(request)

        # Verify that logger.info was called with export event
        assert mock_logger.info.called
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "audit_log_exported"
        assert call_args[1]["actor_id"] == "platform-admin"

    @patch("api.views_audit.logger")
    def test_failed_mfa_check_is_logged(self, mock_logger):
        """Test that failed MFA checks are logged."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
            mfa_level=0,  # No MFA
        )

        from api.views_audit import AuditLogExportView

        view = AuditLogExportView()

        request = type(
            "MockRequest", (), {"user": user, "token_claims": claims, "query_params": {}}
        )()

        view.get(request)

        # Verify that logger.warning was called with MFA denial
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        assert call_args[0][0] == "audit_export_denied_mfa"
        assert call_args[1]["actor_id"] == "platform-admin"
        assert call_args[1]["reason"] == "MFA not verified"


class TestImpersonationLogAuthorization:
    """Tests for impersonation log endpoint authorization."""

    def test_impersonation_logs_require_platform_admin(self):
        """Test that impersonation logs are only accessible to platform admins."""
        user = User.objects.create(username="org-admin", email="admin@org.com")
        claims = create_mock_token_claims(
            user_id="org-admin",
            email="admin@org.com",
            roles=["org_admin"],  # Not platform_admin
        )

        from api.permissions import IsPlatformAdmin

        perm = IsPlatformAdmin()

        request = type("MockRequest", (), {"user": user, "token_claims": claims})()

        # Should deny access
        assert not perm.has_permission(request, None)

    @patch("api.views_impersonation.logger")
    def test_impersonation_log_access_is_logged(self, mock_logger):
        """Test that accessing impersonation logs is logged."""
        user = User.objects.create(username="platform-admin", email="admin@platform.com")
        claims = create_mock_token_claims(
            user_id="platform-admin",
            email="admin@platform.com",
            roles=["platform_admin"],
        )

        from api.views_impersonation import ImpersonationLogListView

        view = ImpersonationLogListView()

        request = type(
            "MockRequest", (), {"user": user, "token_claims": claims, "query_params": {}}
        )()

        view.get(request)

        # Verify that logger.info was called with access event
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert call_args[0][0] == "impersonation_log_accessed"
        assert call_args[1]["actor_id"] == "platform-admin"

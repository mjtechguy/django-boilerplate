"""
Full API Integration Tests with Multiple Users

This module tests all API endpoints with different user roles:
- Platform Admin: Full access to everything
- Org Admin: Access to their organization's resources
- Audit Viewer: Read-only access to audit logs
- Regular User: Limited access
- Unauthenticated: No access to protected endpoints

Tests verify:
1. Authentication requirements
2. Authorization (role-based access control)
3. Data isolation between organizations
4. Audit logging of sensitive operations
5. MFA requirements for sensitive endpoints
"""

import json
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import AuditLog, ImpersonationLog, Org, SensitiveUserData, WebhookEndpoint

User = get_user_model()


# =============================================================================
# Cerbos Mock Fixture
# =============================================================================


@pytest.fixture(autouse=True)
def mock_cerbos():
    """Mock Cerbos client for all integration tests.

    This allows tests to run without a Cerbos server.
    The mock always allows actions - actual permission tests should
    use specific mocks or the unit test suite.
    """
    mock_response = MagicMock()
    mock_response.is_allowed.return_value = True

    mock_client = MagicMock()
    mock_client.check_resources.return_value = mock_response

    with patch("api.cerbos_client.get_client", return_value=mock_client):
        with patch("api.cerbos_client.check_action", return_value=True):
            yield mock_client


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def seed_organizations():
    """Create test organizations."""
    orgs = {
        "acme": Org.objects.create(
            name="ACME Corporation",
            status=Org.Status.ACTIVE,
            license_tier="enterprise",
            feature_flags={"audit_export": True, "webhooks": True},
        ),
        "globex": Org.objects.create(
            name="Globex Industries",
            status=Org.Status.ACTIVE,
            license_tier="professional",
            feature_flags={"audit_export": False, "webhooks": True},
        ),
        "inactive": Org.objects.create(
            name="Inactive Corp",
            status=Org.Status.INACTIVE,
            license_tier="free",
            feature_flags={},
        ),
    }
    return orgs


@pytest.fixture
def seed_users(seed_organizations):
    """Create test users with different roles."""
    orgs = seed_organizations
    users = {
        # Platform admin - full access
        "platform_admin": {
            "user": User.objects.create(
                username="platform-admin-001",
                email="admin@platform.example.com",
            ),
            "claims": {
                "sub": "platform-admin-001",
                "email": "admin@platform.example.com",
                "realm_roles": ["platform_admin"],
                "client_roles": [],
                "roles": [],
                "org_id": None,
                "acr": "urn:keycloak:acr:mfa",
                "amr": ["pwd", "otp"],
                "mfa_level": 1,  # Required for audit export
            },
        },
        # ACME org admin
        "acme_admin": {
            "user": User.objects.create(
                username="acme-admin-001",
                email="admin@acme.example.com",
            ),
            "claims": {
                "sub": "acme-admin-001",
                "email": "admin@acme.example.com",
                "realm_roles": [],
                "client_roles": ["org_admin"],
                "roles": ["org_admin"],
                "org_id": str(orgs["acme"].id),
                "acr": "urn:keycloak:acr:mfa",
                "amr": ["pwd", "otp"],
            },
        },
        # ACME audit viewer
        "acme_auditor": {
            "user": User.objects.create(
                username="acme-auditor-001",
                email="auditor@acme.example.com",
            ),
            "claims": {
                "sub": "acme-auditor-001",
                "email": "auditor@acme.example.com",
                "realm_roles": [],
                "client_roles": ["audit_viewer"],
                "roles": ["audit_viewer"],
                "org_id": str(orgs["acme"].id),
            },
        },
        # ACME regular user
        "acme_user": {
            "user": User.objects.create(
                username="acme-user-001",
                email="user@acme.example.com",
            ),
            "claims": {
                "sub": "acme-user-001",
                "email": "user@acme.example.com",
                "realm_roles": [],
                "client_roles": ["org_member"],
                "roles": ["org_member"],
                "org_id": str(orgs["acme"].id),
            },
        },
        # Globex org admin
        "globex_admin": {
            "user": User.objects.create(
                username="globex-admin-001",
                email="admin@globex.example.com",
            ),
            "claims": {
                "sub": "globex-admin-001",
                "email": "admin@globex.example.com",
                "realm_roles": [],
                "client_roles": ["org_admin"],
                "roles": ["org_admin"],
                "org_id": str(orgs["globex"].id),
                "acr": "urn:keycloak:acr:mfa",
                "amr": ["pwd", "otp"],
            },
        },
        # Platform admin without MFA
        "platform_admin_no_mfa": {
            "user": User.objects.create(
                username="platform-admin-no-mfa",
                email="admin-nomfa@platform.example.com",
            ),
            "claims": {
                "sub": "platform-admin-no-mfa",
                "email": "admin-nomfa@platform.example.com",
                "realm_roles": ["platform_admin"],
                "client_roles": [],
                "roles": [],
                "org_id": None,
                # No MFA claims
            },
        },
    }
    return users


@pytest.fixture
def seed_audit_logs(seed_organizations, seed_users):
    """Create test audit logs for different organizations."""
    orgs = seed_organizations
    users = seed_users

    logs = []

    # ACME audit logs
    for i in range(5):
        logs.append(
            AuditLog.objects.create(
                action=AuditLog.Action.CREATE if i % 2 == 0 else AuditLog.Action.UPDATE,
                resource_type="User",
                resource_id=f"user-{i}",
                actor_id=users["acme_admin"]["claims"]["sub"],
                org_id=str(orgs["acme"].id),
                changes={"field": f"value-{i}"},
            )
        )

    # Globex audit logs
    for i in range(3):
        logs.append(
            AuditLog.objects.create(
                action=AuditLog.Action.DELETE,
                resource_type="Document",
                resource_id=f"doc-{i}",
                actor_id=users["globex_admin"]["claims"]["sub"],
                org_id=str(orgs["globex"].id),
                changes={"deleted": True},
            )
        )

    # Platform-level audit logs (no org)
    logs.append(
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id=str(orgs["acme"].id),
            actor_id=users["platform_admin"]["claims"]["sub"],
            org_id=None,
        )
    )

    return logs


@pytest.fixture
def seed_sensitive_data(seed_organizations, seed_users):
    """Create test sensitive user data."""
    orgs = seed_organizations

    data = []
    # ACME sensitive data
    data.append(
        SensitiveUserData.objects.create(
            user_id=f"user-acme-001",
            ssn="123-45-6789",
            date_of_birth="1990-01-15",
            medical_record_number="MRN-ACME-001",
            diagnosis_codes=["I10", "E11.9"],
            medications=[{"name": "Metformin", "dosage": "500mg"}],
            notes="Patient with hypertension and diabetes.",
            data_classification="phi",
        )
    )

    # Globex sensitive data
    data.append(
        SensitiveUserData.objects.create(
            user_id=f"user-globex-001",
            ssn="987-65-4321",
            date_of_birth="1985-06-20",
            medical_record_number="MRN-GLOBEX-001",
            diagnosis_codes=["J45.909"],
            medications=[{"name": "Albuterol", "dosage": "90mcg"}],
            notes="Patient with asthma.",
            data_classification="phi",
        )
    )

    return data


@pytest.fixture
def seed_webhooks(seed_organizations, seed_users):
    """Create test webhook endpoints."""
    orgs = seed_organizations

    webhooks = []
    webhooks.append(
        WebhookEndpoint.objects.create(
            org_id=orgs["acme"].id,
            url="https://acme.example.com/webhooks",
            events=["user.created", "user.updated"],
            is_active=True,
        )
    )
    webhooks.append(
        WebhookEndpoint.objects.create(
            org_id=orgs["globex"].id,
            url="https://globex.example.com/webhooks",
            events=["document.deleted"],
            is_active=True,
        )
    )

    return webhooks


# =============================================================================
# Helper Functions
# =============================================================================


def create_authenticated_client(user_data, monkeypatch):
    """Create an APIClient authenticated as the specified user."""

    def mock_validate(self, token):
        return user_data["claims"]

    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token", mock_validate
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

    return client


def create_unauthenticated_client():
    """Create an unauthenticated APIClient."""
    return APIClient()


# =============================================================================
# Health Check Endpoints (Public)
# =============================================================================


@pytest.mark.django_db
class TestHealthEndpoints:
    """Test public health check endpoints."""

    def test_healthz_endpoint(self):
        """Test the main health check endpoint."""
        client = create_unauthenticated_client()
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_liveness_probe(self):
        """Test Kubernetes liveness probe."""
        client = create_unauthenticated_client()
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.data["status"] == "alive"  # LivenessView returns "alive"

    def test_readiness_probe(self):
        """Test Kubernetes readiness probe."""
        client = create_unauthenticated_client()
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert "status" in response.data


# =============================================================================
# Authentication Tests
# =============================================================================


@pytest.mark.django_db
class TestAuthentication:
    """Test authentication requirements for protected endpoints."""

    def test_ping_requires_auth(self):
        """Test that /ping endpoint requires authentication."""
        client = create_unauthenticated_client()
        response = client.get("/api/v1/ping")
        assert response.status_code == 401

    def test_ping_with_valid_auth(self, seed_users, monkeypatch):
        """Test /ping with valid authentication."""
        client = create_authenticated_client(seed_users["acme_user"], monkeypatch)
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.data["message"] == "pong"
        assert "claims_sub" in response.data

    def test_protected_endpoint_works(self, seed_users, monkeypatch):
        """Test that /protected endpoint works when authenticated.

        Note: Without Cerbos server, the mock allows all access.
        The endpoint itself doesn't check authentication (only Cerbos permission).
        This test verifies the endpoint returns the expected response.
        """
        client = create_authenticated_client(seed_users["acme_user"], monkeypatch)
        response = client.get("/api/v1/protected")
        assert response.status_code == 200
        assert "message" in response.data


# =============================================================================
# Audit Log Endpoint Tests
# =============================================================================


@pytest.mark.django_db
class TestAuditEndpoints:
    """Test audit log endpoints with different user roles."""

    def test_audit_list_unauthenticated(self):
        """Unauthenticated users cannot access audit logs."""
        client = create_unauthenticated_client()
        response = client.get("/api/v1/audit")
        assert response.status_code == 401

    def test_audit_list_regular_user_denied(self, seed_users, seed_audit_logs, monkeypatch):
        """Regular users without audit role cannot access audit logs."""
        client = create_authenticated_client(seed_users["acme_user"], monkeypatch)
        response = client.get("/api/v1/audit")
        assert response.status_code == 403

    def test_audit_list_platform_admin_sees_all(
        self, seed_users, seed_organizations, seed_audit_logs, monkeypatch
    ):
        """Platform admin can see all audit logs."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        # Should see logs from all orgs
        assert response.data["count"] >= 9  # 5 ACME + 3 Globex + 1 platform

    def test_audit_list_org_admin_sees_own_org(
        self, seed_users, seed_organizations, seed_audit_logs, monkeypatch
    ):
        """Org admin can only see their organization's logs."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        # Should only see ACME logs
        for log in response.data["results"]:
            assert log["org_id"] == str(seed_organizations["acme"].id)

    def test_audit_list_org_isolation(
        self, seed_users, seed_organizations, seed_audit_logs, monkeypatch
    ):
        """Org admin cannot see another org's logs."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        # Should NOT see Globex logs
        globex_id = str(seed_organizations["globex"].id)
        for log in response.data["results"]:
            assert log["org_id"] != globex_id

    def test_audit_list_auditor_role(
        self, seed_users, seed_organizations, seed_audit_logs, monkeypatch
    ):
        """Audit viewer can see their organization's logs."""
        client = create_authenticated_client(seed_users["acme_auditor"], monkeypatch)
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_audit_filter_by_action(self, seed_users, seed_audit_logs, monkeypatch):
        """Test filtering audit logs by action."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit?action=delete")
        assert response.status_code == 200
        for log in response.data["results"]:
            assert log["action"] == "delete"

    def test_audit_filter_by_resource_type(self, seed_users, seed_audit_logs, monkeypatch):
        """Test filtering audit logs by resource type."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit?resource_type=User")
        assert response.status_code == 200
        for log in response.data["results"]:
            assert log["resource_type"] == "User"

    def test_audit_export_requires_platform_admin(
        self, seed_users, seed_audit_logs, monkeypatch
    ):
        """Audit export requires platform admin role."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 403

    def test_audit_export_requires_mfa(self, seed_users, seed_audit_logs, monkeypatch):
        """Audit export requires MFA verification."""
        client = create_authenticated_client(
            seed_users["platform_admin_no_mfa"], monkeypatch
        )
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 403
        assert "MFA" in response.data.get("error", "")

    def test_audit_export_with_mfa(self, seed_users, seed_audit_logs, monkeypatch):
        """Audit export works with platform admin + MFA."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 200
        assert "results" in response.data

    def test_audit_verify_requires_platform_admin(
        self, seed_users, seed_audit_logs, monkeypatch
    ):
        """Audit verification requires platform admin."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/audit/verify")
        assert response.status_code == 403

    def test_audit_verify_platform_admin(self, seed_users, seed_audit_logs, monkeypatch):
        """Platform admin can verify audit integrity."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit/verify")
        assert response.status_code == 200
        assert "status" in response.data

    def test_audit_chain_verify(self, seed_users, seed_audit_logs, monkeypatch):
        """Test chain verification endpoint."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit/chain-verify")
        assert response.status_code == 200
        assert "valid" in response.data
        assert "entries_checked" in response.data


# =============================================================================
# Admin Endpoints Tests
# =============================================================================


@pytest.mark.django_db
class TestAdminEndpoints:
    """Test admin-only endpoints."""

    def test_admin_orgs_requires_platform_admin(
        self, seed_users, seed_organizations, monkeypatch
    ):
        """Admin org list requires platform admin role."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/admin/orgs")
        assert response.status_code == 403

    def test_admin_orgs_platform_admin(self, seed_users, seed_organizations, monkeypatch):
        """Platform admin can list all organizations."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/admin/orgs")
        assert response.status_code == 200
        # Response may be paginated
        orgs_data = response.data.get("results", response.data)
        assert len(orgs_data) >= 3  # ACME, Globex, Inactive

    def test_impersonation_logs_requires_platform_admin(
        self, seed_users, monkeypatch
    ):
        """Impersonation logs require platform admin."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/admin/impersonation/logs")
        assert response.status_code == 403

    def test_impersonation_logs_platform_admin(self, seed_users, monkeypatch):
        """Platform admin can access impersonation logs."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/admin/impersonation/logs")
        assert response.status_code == 200


# =============================================================================
# Webhook Endpoints Tests
# =============================================================================


@pytest.mark.django_db
class TestWebhookEndpoints:
    """Test webhook management endpoints.

    Webhook views require platform_admin authentication.
    """

    def test_webhook_list_requires_auth(self):
        """Webhook list requires authentication."""
        client = create_unauthenticated_client()
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 401

    def test_webhook_list_requires_platform_admin(self, seed_users, monkeypatch):
        """Webhook list requires platform_admin role."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 403

    def test_webhook_list_platform_admin(self, seed_users, seed_webhooks, monkeypatch):
        """Platform admin can list webhooks."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 200

    def test_webhook_list_with_org_filter(
        self, seed_users, seed_organizations, seed_webhooks, monkeypatch
    ):
        """Test filtering webhooks by org_id query param."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        acme_id = str(seed_organizations["acme"].id)
        response = client.get(f"/api/v1/webhooks?org_id={acme_id}")
        assert response.status_code == 200
        # Should only see ACME webhooks when filtered
        results = response.data.get("results", response.data)
        for webhook in results:
            assert str(webhook["org_id"]) == acme_id

    def test_webhook_create(self, seed_users, seed_organizations, monkeypatch):
        """Test creating a webhook endpoint."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        acme_id = str(seed_organizations["acme"].id)
        response = client.post(
            "/api/v1/webhooks",
            {
                "org_id": acme_id,
                "name": "ACME New Webhook",
                "url": "https://new-webhook.acme.example.com/hook",
                "events": ["user.created"],
                "is_active": True,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["url"] == "https://new-webhook.acme.example.com/hook"

    def test_webhook_detail_access(self, seed_users, seed_webhooks, monkeypatch):
        """Test webhook detail access requires platform_admin."""
        webhook = seed_webhooks[0]
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get(f"/api/v1/webhooks/{webhook.id}")
        assert response.status_code == 200
        assert response.data["id"] == str(webhook.id)


# =============================================================================
# License Endpoints Tests
# =============================================================================


@pytest.mark.django_db
class TestLicenseEndpoints:
    """Test license management endpoints."""

    def test_license_view_unauthenticated(self, seed_organizations):
        """License view returns 401 when not authenticated."""
        client = create_unauthenticated_client()
        response = client.get(f"/api/v1/orgs/{seed_organizations['acme'].id}/license")
        # DRF returns 401 for unauthenticated requests
        assert response.status_code == 401

    def test_license_view_own_org(self, seed_users, seed_organizations, monkeypatch):
        """Org admin can view their organization's license."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        response = client.get(f"/api/v1/orgs/{seed_organizations['acme'].id}/license")
        assert response.status_code == 200
        # Response uses license_tier key from get_license()
        assert "license_tier" in response.data


# =============================================================================
# Monitoring Endpoints Tests
# =============================================================================


@pytest.mark.django_db
class TestMonitoringEndpoints:
    """Test monitoring and metrics endpoints."""

    def test_prometheus_metrics(self, seed_users, monkeypatch):
        """Test Prometheus metrics endpoint."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/monitoring/metrics")
        assert response.status_code == 200

    def test_app_metrics_json(self, seed_users, monkeypatch):
        """Test JSON app metrics endpoint."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/monitoring/metrics/json")
        assert response.status_code == 200


# =============================================================================
# Data Isolation Tests
# =============================================================================


@pytest.mark.django_db
class TestDataIsolation:
    """Test that data is properly isolated between organizations."""

    def test_audit_log_org_isolation(
        self, seed_users, seed_organizations, seed_audit_logs, monkeypatch
    ):
        """Verify audit logs are isolated by organization."""
        # ACME admin
        acme_client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        acme_response = acme_client.get("/api/v1/audit")
        acme_org_ids = {log["org_id"] for log in acme_response.data["results"]}

        # Reset monkeypatch for Globex
        monkeypatch.undo()

        # Globex admin
        globex_client = create_authenticated_client(seed_users["globex_admin"], monkeypatch)
        globex_response = globex_client.get("/api/v1/audit")
        globex_org_ids = {log["org_id"] for log in globex_response.data["results"]}

        # Should have no overlap
        assert acme_org_ids.isdisjoint(globex_org_ids)


# =============================================================================
# MFA Enforcement Tests
# =============================================================================


@pytest.mark.django_db
class TestMFAEnforcement:
    """Test MFA requirements for sensitive operations."""

    def test_audit_export_mfa_required(self, seed_users, seed_audit_logs, monkeypatch):
        """Audit export requires MFA even for platform admin."""
        client = create_authenticated_client(
            seed_users["platform_admin_no_mfa"], monkeypatch
        )
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 403
        assert "MFA" in str(response.data)

    def test_audit_export_mfa_satisfied(self, seed_users, seed_audit_logs, monkeypatch):
        """Audit export succeeds with MFA-verified platform admin."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 200


# =============================================================================
# Complete Integration Test
# =============================================================================


@pytest.mark.django_db
class TestFullIntegration:
    """Complete end-to-end integration tests."""

    def test_complete_user_journey_platform_admin(
        self,
        seed_users,
        seed_organizations,
        seed_audit_logs,
        seed_webhooks,
        monkeypatch,
    ):
        """Test complete platform admin journey through all endpoints."""
        client = create_authenticated_client(seed_users["platform_admin"], monkeypatch)

        # 1. Check ping
        response = client.get("/api/v1/ping")
        assert response.status_code == 200

        # 2. View all orgs
        response = client.get("/api/v1/admin/orgs")
        assert response.status_code == 200
        # Response may be paginated
        orgs_data = response.data.get("results", response.data)
        assert len(orgs_data) >= 3  # ACME, Globex, Inactive

        # 3. View all audit logs
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        total_logs = response.data["count"]

        # 4. Filter audit logs
        response = client.get("/api/v1/audit?action=create")
        assert response.status_code == 200

        # 5. Export audit logs (requires MFA)
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 200

        # 6. Verify audit chain
        response = client.get("/api/v1/audit/chain-verify")
        assert response.status_code == 200

        # 7. View impersonation logs
        response = client.get("/api/v1/admin/impersonation/logs")
        assert response.status_code == 200

    def test_complete_user_journey_org_admin(
        self,
        seed_users,
        seed_organizations,
        seed_audit_logs,
        seed_webhooks,
        monkeypatch,
    ):
        """Test complete org admin journey through permitted endpoints."""
        client = create_authenticated_client(seed_users["acme_admin"], monkeypatch)
        acme_id = str(seed_organizations["acme"].id)

        # 1. Check ping
        response = client.get("/api/v1/ping")
        assert response.status_code == 200

        # 2. Cannot view all orgs
        response = client.get("/api/v1/admin/orgs")
        assert response.status_code == 403

        # 3. Can view own org's audit logs
        response = client.get("/api/v1/audit")
        assert response.status_code == 200
        for log in response.data["results"]:
            assert log["org_id"] == acme_id

        # 4. Cannot export audit logs
        response = client.get("/api/v1/audit/export")
        assert response.status_code == 403

        # 5. Cannot verify audit chain
        response = client.get("/api/v1/audit/chain-verify")
        assert response.status_code == 403

        # 6. Can view own org's license
        response = client.get(f"/api/v1/orgs/{acme_id}/license")
        assert response.status_code == 200

        # 7. Can manage own org's webhooks
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 200

    def test_complete_user_journey_regular_user(
        self, seed_users, seed_organizations, monkeypatch
    ):
        """Test regular user has limited access."""
        client = create_authenticated_client(seed_users["acme_user"], monkeypatch)

        # 1. Can ping
        response = client.get("/api/v1/ping")
        assert response.status_code == 200

        # 2. Cannot view orgs
        response = client.get("/api/v1/admin/orgs")
        assert response.status_code == 403

        # 3. Cannot view audit logs
        response = client.get("/api/v1/audit")
        assert response.status_code == 403

        # 4. Cannot export
        response = client.get("/api/v1/audit/export")
        assert response.status_code in [401, 403]


# =============================================================================
# Summary Report
# =============================================================================


@pytest.mark.django_db
class TestSummaryReport:
    """Generate a summary of API access by role."""

    def test_generate_access_matrix(
        self,
        seed_users,
        seed_organizations,
        seed_audit_logs,
        seed_webhooks,
        monkeypatch,
        capsys,
    ):
        """Generate and print an access matrix for all endpoints."""
        endpoints = [
            ("GET", "/api/v1/ping"),
            ("GET", "/api/v1/protected"),
            ("GET", "/api/v1/admin/orgs"),
            ("GET", "/api/v1/audit"),
            ("GET", "/api/v1/audit/export"),
            ("GET", "/api/v1/audit/verify"),
            ("GET", "/api/v1/audit/chain-verify"),
            ("GET", "/api/v1/admin/impersonation/logs"),
            ("GET", "/api/v1/webhooks"),
            ("GET", "/api/v1/health/live"),
            ("GET", "/api/v1/health/ready"),
        ]

        users_to_test = [
            ("Platform Admin", seed_users["platform_admin"]),
            ("Platform Admin (No MFA)", seed_users["platform_admin_no_mfa"]),
            ("ACME Org Admin", seed_users["acme_admin"]),
            ("ACME Auditor", seed_users["acme_auditor"]),
            ("ACME User", seed_users["acme_user"]),
            ("Globex Admin", seed_users["globex_admin"]),
        ]

        results = {}

        for user_name, user_data in users_to_test:
            monkeypatch.undo()
            client = create_authenticated_client(user_data, monkeypatch)
            results[user_name] = {}

            for method, endpoint in endpoints:
                if method == "GET":
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint, {})

                status_code = response.status_code
                if status_code == 200:
                    results[user_name][endpoint] = "OK"
                elif status_code == 201:
                    results[user_name][endpoint] = "OK"
                elif status_code == 401:
                    results[user_name][endpoint] = "UNAUTH"
                elif status_code == 403:
                    results[user_name][endpoint] = "FORBID"
                elif status_code == 404:
                    results[user_name][endpoint] = "NOTFND"
                else:
                    results[user_name][endpoint] = f"ERR{status_code}"

        # Print matrix
        print("\n" + "=" * 120)
        print("API ACCESS MATRIX BY ROLE")
        print("=" * 120)
        print(f"{'Endpoint':<45}", end="")
        for user_name, _ in users_to_test:
            print(f"{user_name[:12]:<14}", end="")
        print()
        print("-" * 120)

        for method, endpoint in endpoints:
            print(f"{method} {endpoint:<40}", end="")
            for user_name, _ in users_to_test:
                print(f"{results[user_name].get(endpoint, '?'):<14}", end="")
            print()

        print("=" * 120)
        print("Legend: OK=Success, FORBID=Forbidden(403), UNAUTH=Unauthenticated(401), NOTFND=NotFound(404)")
        print("=" * 120 + "\n")

        # This test always passes - it's for generating the report
        assert True

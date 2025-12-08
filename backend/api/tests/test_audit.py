"""
Tests for the audit logging system.

Tests cover:
- AuditLog model creation
- log_audit function (sync and async)
- Signal handlers for automatic audit logging
- REST API endpoint with filters
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from api.audit import log_audit, log_audit_async
from api.models import AuditLog, Org, SampleResource

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestAuditLogModel:
    """Tests for AuditLog model."""

    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        audit = AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="123",
            actor_id="user-456",
            actor_email="test@example.com",
            org_id="org-789",
            changes={"name": {"old": None, "new": "Acme Corp"}},
            metadata={"ip": "192.168.1.1"},
            request_id="req-abc",
        )

        assert audit.id is not None
        assert audit.action == AuditLog.Action.CREATE
        assert audit.resource_type == "Org"
        assert audit.resource_id == "123"
        assert audit.actor_id == "user-456"
        assert audit.actor_email == "test@example.com"
        assert audit.org_id == "org-789"
        assert audit.changes == {"name": {"old": None, "new": "Acme Corp"}}
        assert audit.metadata == {"ip": "192.168.1.1"}
        assert audit.request_id == "req-abc"
        assert audit.timestamp is not None

    def test_audit_log_ordering(self):
        """Test that audit logs are ordered by timestamp descending."""
        # Create three audit logs with different timestamps
        old_log = AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user",
        )
        # Manually set timestamp to be older
        old_log.timestamp = timezone.now() - timedelta(hours=2)
        old_log.save()

        middle_log = AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user",
        )
        middle_log.timestamp = timezone.now() - timedelta(hours=1)
        middle_log.save()

        new_log = AuditLog.objects.create(
            action=AuditLog.Action.DELETE,
            resource_type="Org",
            resource_id="1",
            actor_id="user",
        )

        # Query should return newest first
        logs = list(AuditLog.objects.all()[:3])
        assert logs[0].id == new_log.id
        assert logs[1].id == middle_log.id
        assert logs[2].id == old_log.id

    def test_audit_log_str_representation(self):
        """Test string representation of AuditLog."""
        audit = AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id="123",
            actor_id="user",
        )
        assert str(audit) == "AuditLog<update Org:123>"


class TestLogAuditFunction:
    """Tests for log_audit function."""

    def test_log_audit_basic(self):
        """Test basic audit logging."""
        audit = log_audit(
            action=AuditLog.Action.CREATE,
            resource_type="TestResource",
            resource_id="test-123",
            actor_id="user-456",
        )

        assert audit.action == AuditLog.Action.CREATE
        assert audit.resource_type == "TestResource"
        assert audit.resource_id == "test-123"
        assert audit.actor_id == "user-456"

    def test_log_audit_with_changes(self):
        """Test audit logging with field changes."""
        changes = {
            "name": {"old": "Old Name", "new": "New Name"},
            "status": {"old": "active", "new": "inactive"},
        }

        audit = log_audit(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id="org-123",
            changes=changes,
            actor_id="user-456",
        )

        assert audit.changes == changes

    def test_log_audit_with_metadata(self):
        """Test audit logging with metadata."""
        metadata = {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"}

        audit = log_audit(
            action=AuditLog.Action.LOGIN,
            resource_type="User",
            resource_id="user-123",
            metadata=metadata,
            actor_id="user-123",
        )

        assert audit.metadata == metadata

    @patch("api.audit.get_request_context")
    def test_log_audit_uses_request_context(self, mock_get_context):
        """Test that log_audit uses request context when actor/org not provided."""
        mock_get_context.return_value = {
            "actor": "context-user-123",
            "org_id": "context-org-456",
            "request_id": "req-789",
        }

        audit = log_audit(
            action=AuditLog.Action.READ,
            resource_type="Resource",
            resource_id="res-123",
        )

        assert audit.actor_id == "context-user-123"
        assert audit.org_id == "context-org-456"
        assert audit.request_id == "req-789"

    @patch("api.audit.get_request_context")
    def test_log_audit_explicit_actor_overrides_context(self, mock_get_context):
        """Test that explicit actor_id overrides request context."""
        mock_get_context.return_value = {
            "actor": "context-user-123",
            "org_id": "context-org-456",
        }

        audit = log_audit(
            action=AuditLog.Action.CREATE,
            resource_type="Resource",
            resource_id="res-123",
            actor_id="explicit-user-789",
        )

        assert audit.actor_id == "explicit-user-789"

    def test_log_audit_pii_masking(self, settings):
        """Test PII masking based on AUDIT_PII_POLICY."""
        settings.AUDIT_PII_POLICY = "mask"

        audit = log_audit(
            action=AuditLog.Action.CREATE,
            resource_type="User",
            resource_id="user-123",
            actor_id="user-123",
            actor_email="john.doe@example.com",
        )

        # Email should be masked
        assert audit.actor_email == "jo***om"

    def test_log_audit_pii_hashing(self, settings):
        """Test PII hashing based on AUDIT_PII_POLICY."""
        settings.AUDIT_PII_POLICY = "hash"

        audit = log_audit(
            action=AuditLog.Action.CREATE,
            resource_type="User",
            resource_id="user-123",
            actor_id="user-123",
            actor_email="john.doe@example.com",
        )

        # Email should be hashed (16 character hex string)
        assert len(audit.actor_email) == 16
        assert audit.actor_email != "john.doe@example.com"

    def test_log_audit_pii_drop(self, settings):
        """Test PII dropping based on AUDIT_PII_POLICY."""
        settings.AUDIT_PII_POLICY = "drop"

        audit = log_audit(
            action=AuditLog.Action.CREATE,
            resource_type="User",
            resource_id="user-123",
            actor_id="user-123",
            actor_email="john.doe@example.com",
        )

        # Email should be dropped (None)
        assert audit.actor_email is None


class TestLogAuditAsync:
    """Tests for async audit logging via Celery."""

    @patch("api.tasks.log_audit_task")
    def test_log_audit_async_queues_task(self, mock_task):
        """Test that log_audit_async queues a Celery task."""
        mock_task.delay.return_value = None

        log_audit_async(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="org-123",
            actor_id="user-456",
        )

        # Verify task was queued
        mock_task.delay.assert_called_once()
        call_kwargs = mock_task.delay.call_args[1]
        assert call_kwargs["action"] == AuditLog.Action.CREATE
        assert call_kwargs["resource_type"] == "Org"
        assert call_kwargs["resource_id"] == "org-123"


class TestAuditSignals:
    """Tests for automatic audit logging via Django signals."""

    def test_org_create_signal(self):
        """Test that creating an Org triggers audit log."""
        org = Org.objects.create(name="Test Org")

        # Should have created an audit log
        audit = AuditLog.objects.filter(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id=str(org.id),
        ).first()

        assert audit is not None
        assert "name" in audit.changes
        assert audit.changes["name"]["new"] == "Test Org"

    def test_org_update_signal(self):
        """Test that updating an Org triggers audit log."""
        org = Org.objects.create(name="Original Name")

        # Clear existing audit logs
        AuditLog.objects.all().delete()

        # Update the org
        org.name = "Updated Name"
        org.save()

        # Should have created an update audit log
        audit = AuditLog.objects.filter(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id=str(org.id),
        ).first()

        assert audit is not None
        assert "name" in audit.changes
        assert audit.changes["name"]["old"] == "Original Name"
        assert audit.changes["name"]["new"] == "Updated Name"

    def test_org_delete_signal(self):
        """Test that deleting an Org triggers audit log."""
        org = Org.objects.create(name="To Delete")
        org_id = str(org.id)

        # Clear existing audit logs
        AuditLog.objects.all().delete()

        # Delete the org
        org.delete()

        # Should have created a delete audit log
        audit = AuditLog.objects.filter(
            action=AuditLog.Action.DELETE,
            resource_type="Org",
            resource_id=org_id,
        ).first()

        assert audit is not None
        assert audit.metadata["name"] == "To Delete"

    def test_sample_resource_signals(self):
        """Test audit logging for SampleResource."""
        org = Org.objects.create(name="Test Org")

        # Clear existing audit logs
        AuditLog.objects.all().delete()

        # Create a sample resource
        resource = SampleResource.objects.create(org=org, name="Test Resource")

        # Should have created an audit log
        audit = AuditLog.objects.filter(
            action=AuditLog.Action.CREATE,
            resource_type="SampleResource",
            resource_id=str(resource.id),
        ).first()

        assert audit is not None
        assert audit.org_id == str(org.id)


class TestAuditAPIEndpoint:
    """Tests for the audit log REST API endpoint.

    These tests focus on the API's filtering and pagination functionality.
    Authorization tests are in test_audit_authorization.py.
    """

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated APIClient.

        Note: We bypass authorization checks here since they're tested
        separately in test_audit_authorization.py. These tests focus on
        the API's filtering and data handling functionality.
        """
        user = User.objects.create(username="test-user", email="test@example.com")
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    @pytest.fixture
    def bypass_auth(self):
        """Fixture that bypasses permission checks for these functional tests."""
        with patch("api.permissions.IsAuditViewer.has_permission", return_value=True):
            with patch(
                "api.views_audit.getattr",
                side_effect=lambda obj, attr, default=None: (
                    {"realm_roles": ["platform_admin"], "org_id": None}
                    if attr == "token_claims"
                    else getattr(obj, attr, default)
                ),
            ):
                yield

    def test_list_audit_logs(self, authenticated_client, bypass_auth):
        """Test listing audit logs via API."""
        # Create some audit logs
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user-1",
        )
        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id="2",
            actor_id="user-2",
        )

        response = authenticated_client.get("/api/v1/audit")

        assert response.status_code == 200
        assert response.data["count"] >= 2
        assert len(response.data["results"]) >= 2

    def test_filter_by_org_id(self, authenticated_client, bypass_auth):
        """Test filtering audit logs by org_id."""
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user-1",
            org_id="org-123",
        )
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="2",
            actor_id="user-2",
            org_id="org-456",
        )

        response = authenticated_client.get("/api/v1/audit?org_id=org-123")

        assert response.status_code == 200
        assert all(log["org_id"] == "org-123" for log in response.data["results"])

    def test_filter_by_action(self, authenticated_client, bypass_auth):
        """Test filtering audit logs by action."""
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user-1",
        )
        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            resource_type="Org",
            resource_id="2",
            actor_id="user-2",
        )

        response = authenticated_client.get("/api/v1/audit?action=create")

        assert response.status_code == 200
        assert all(log["action"] == "create" for log in response.data["results"])

    def test_filter_by_resource_type(self, authenticated_client, bypass_auth):
        """Test filtering audit logs by resource_type."""
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user-1",
        )
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="User",
            resource_id="2",
            actor_id="user-2",
        )

        response = authenticated_client.get("/api/v1/audit?resource_type=Org")

        assert response.status_code == 200
        assert all(log["resource_type"] == "Org" for log in response.data["results"])

    def test_pagination(self, authenticated_client, bypass_auth):
        """Test pagination of audit logs."""
        # Create 25 audit logs
        for i in range(25):
            AuditLog.objects.create(
                action=AuditLog.Action.CREATE,
                resource_type="Org",
                resource_id=str(i),
                actor_id="user-1",
            )

        # Get first page
        response = authenticated_client.get("/api/v1/audit?limit=10&offset=0")
        assert response.status_code == 200
        assert len(response.data["results"]) == 10
        assert response.data["count"] >= 25
        assert response.data["limit"] == 10
        assert response.data["offset"] == 0

        # Get second page
        response = authenticated_client.get("/api/v1/audit?limit=10&offset=10")
        assert response.status_code == 200
        assert len(response.data["results"]) == 10
        assert response.data["offset"] == 10

    def test_date_range_filter(self, authenticated_client, bypass_auth):
        """Test filtering by date range."""
        # Create audit logs with different timestamps
        old_log = AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="1",
            actor_id="user-1",
        )
        old_log.timestamp = timezone.now() - timedelta(days=2)
        old_log.save()

        new_log = AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            resource_type="Org",
            resource_id="2",
            actor_id="user-1",
        )

        # Filter for logs from the last day
        start_date = (timezone.now() - timedelta(days=1)).isoformat()
        response = authenticated_client.get(f"/api/v1/audit?start_date={start_date}")

        assert response.status_code == 200
        # Should only include the new log
        assert str(new_log.id) in [log["id"] for log in response.data["results"]]

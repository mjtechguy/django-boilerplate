"""
End-to-end integration tests for account lockout notification flow.

These tests verify the complete lockout notification system from trigger to
notification, testing both django-axes and local auth lockout paths.

Tests cover:
- Failed login attempts trigger lockout and notifications
- Lockout creates audit log entries
- User notification emails are queued
- Mass lockout detection and admin alerts
- Integration between signals, tasks, and tracking systems
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch, call

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import AuditLog
from api.models_local_auth import LocalUserProfile
from api.signals_lockout import handle_user_locked_out

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestLocalAuthLockoutFlow:
    """End-to-end tests for local auth lockout notification flow."""

    @pytest.fixture
    def user(self):
        """Create a test user with email."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

    @pytest.fixture
    def user_without_email(self):
        """Create a test user without email."""
        return User.objects.create_user(
            username="noemailuser",
            email="",
            first_name="NoEmail",
        )

    @pytest.fixture
    def local_profile(self, user):
        """Create a local user profile."""
        profile = LocalUserProfile.objects.create(
            user=user,
            password_hash="hashed_password",
        )
        profile.set_password("correct_password")
        profile.save()
        return profile

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for tracking tests."""
        mock_client = MagicMock()
        mock_client.zadd.return_value = 1
        mock_client.zcard.return_value = 1
        mock_client.zremrangebyscore.return_value = 0
        mock_client.expire.return_value = True
        mock_client.hset.return_value = True
        mock_client.zrangebyscore.return_value = []
        return mock_client

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_failed_login_attempts_trigger_lockout(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
        user,
    ):
        """Test that failed login attempts trigger lockout and notification."""
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)
        ip_address = "192.168.1.100"

        # Record failed attempts up to the limit
        for i in range(max_attempts):
            local_profile.record_login_attempt(
                success=False,
                ip_address=ip_address,
            )

        # Verify profile is locked
        local_profile.refresh_from_db()
        assert local_profile.locked_until is not None
        assert local_profile.failed_login_attempts == max_attempts
        assert local_profile.locked_until > timezone.now()

        # Verify notification task was queued
        assert mock_notification_task.delay.called
        call_kwargs = mock_notification_task.delay.call_args[1]
        assert call_kwargs["user_email"] == user.email
        assert call_kwargs["user_data"]["username"] == user.username
        assert call_kwargs["user_data"]["first_name"] == user.first_name
        assert call_kwargs["lockout_data"]["ip_address"] == ip_address
        assert call_kwargs["lockout_data"]["failure_count"] == max_attempts

        # Verify audit log was created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None
        assert audit_log.actor_id == str(user.id)
        assert audit_log.actor_email == user.email
        assert audit_log.metadata["ip_address"] == ip_address
        assert audit_log.metadata["source"] == "local-auth"
        assert audit_log.metadata["failure_count"] == max_attempts

        # Verify mass lockout tracking was incremented
        mock_increment.assert_called_once_with(
            username=user.username,
            email=user.email,
            ip_address=ip_address,
            source="local-auth",
        )

        # Verify check_mass_lockout_task was triggered
        mock_check_task.delay.assert_called_once()

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_lockout_creates_audit_log(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
        user,
    ):
        """Test that lockout creates a complete audit log entry."""
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)
        ip_address = "192.168.1.200"

        # Trigger lockout
        for i in range(max_attempts):
            local_profile.record_login_attempt(success=False, ip_address=ip_address)

        # Verify audit log has all required fields
        audit_logs = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        )
        assert audit_logs.count() == 1

        audit_log = audit_logs.first()
        assert audit_log.action == "account_locked"
        assert audit_log.resource_type == "User"
        assert audit_log.resource_id == str(user.id)
        assert audit_log.actor_id == str(user.id)
        assert audit_log.actor_email == user.email

        # Verify metadata contains all required information
        assert "ip_address" in audit_log.metadata
        assert audit_log.metadata["ip_address"] == ip_address
        assert "failure_count" in audit_log.metadata
        assert audit_log.metadata["failure_count"] == max_attempts
        assert "lockout_duration_minutes" in audit_log.metadata
        assert "unlock_time" in audit_log.metadata
        assert "source" in audit_log.metadata
        assert audit_log.metadata["source"] == "local-auth"

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_email_queued_for_user(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
        user,
    ):
        """Test that user notification email is queued via Celery."""
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)
        ip_address = "192.168.1.150"

        # Trigger lockout
        for i in range(max_attempts):
            local_profile.record_login_attempt(success=False, ip_address=ip_address)

        # Verify notification task was called exactly once
        assert mock_notification_task.delay.call_count == 1

        # Verify notification task was called with correct parameters
        call_kwargs = mock_notification_task.delay.call_args[1]

        # Check user email
        assert call_kwargs["user_email"] == user.email

        # Check user data
        user_data = call_kwargs["user_data"]
        assert user_data["username"] == user.username
        assert user_data["email"] == user.email
        assert user_data["first_name"] == user.first_name

        # Check lockout data
        lockout_data = call_kwargs["lockout_data"]
        assert lockout_data["ip_address"] == ip_address
        assert lockout_data["failure_count"] == max_attempts
        assert "lockout_duration" in lockout_data
        assert "lockout_time" in lockout_data
        assert "unlock_time" in lockout_data

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_no_email_sent_when_user_has_no_email(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user_without_email,
    ):
        """Test that no email is queued when user has no email address."""
        profile = LocalUserProfile.objects.create(
            user=user_without_email,
            password_hash="hashed_password",
        )
        profile.set_password("password123")
        profile.save()
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Trigger lockout
        for i in range(max_attempts):
            profile.record_login_attempt(success=False, ip_address="192.168.1.99")

        # Verify lockout occurred
        profile.refresh_from_db()
        assert profile.locked_until is not None

        # Verify notification task was NOT called (no email)
        assert not mock_notification_task.delay.called

        # Verify audit log was still created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_id=str(user_without_email.id),
        ).first()
        assert audit_log is not None

        # Verify mass tracking still occurred
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()


class TestAxesLockoutFlow:
    """End-to-end tests for django-axes lockout notification flow."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="axesuser",
            email="axes@example.com",
            first_name="Axes",
            last_name="User",
        )

    @pytest.fixture
    def request_factory(self):
        """Create a request factory."""
        return RequestFactory()

    @pytest.fixture
    def mock_request(self, request_factory):
        """Create a mock request."""
        return request_factory.get("/login")

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_axes_signal_triggers_complete_flow(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user,
        mock_request,
    ):
        """Test that django-axes signal triggers complete notification flow."""
        mock_increment.return_value = 1
        ip_address = "10.0.0.50"

        # Simulate axes signal
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=user.username,
            ip_address=ip_address,
        )

        # Verify notification task was called
        assert mock_notification_task.delay.called
        call_kwargs = mock_notification_task.delay.call_args[1]
        assert call_kwargs["user_email"] == user.email
        assert call_kwargs["user_data"]["username"] == user.username
        assert call_kwargs["lockout_data"]["ip_address"] == ip_address
        assert call_kwargs["lockout_data"]["failure_count"] == settings.AXES_FAILURE_LIMIT

        # Verify audit log was created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None
        assert audit_log.metadata["source"] == "django-axes"
        assert audit_log.metadata["ip_address"] == ip_address

        # Verify mass lockout tracking
        mock_increment.assert_called_once_with(
            username=user.username,
            email=user.email,
            ip_address=ip_address,
            source="django-axes",
        )
        mock_check_task.delay.assert_called_once()

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_axes_lockout_with_nonexistent_user(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        mock_request,
    ):
        """Test axes lockout when user doesn't exist in database."""
        mock_increment.return_value = 1
        username = "nonexistent"
        ip_address = "10.0.0.99"

        # Simulate axes signal
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=username,
            ip_address=ip_address,
        )

        # Verify notification task was NOT called (no user)
        assert not mock_notification_task.delay.called

        # Verify audit log was still created with username as fallback
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=username,
        ).first()
        assert audit_log is not None
        assert audit_log.actor_id == username
        assert audit_log.metadata["source"] == "django-axes"

        # Verify mass tracking still occurred
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()


class TestMassLockoutDetection:
    """End-to-end tests for mass lockout detection and admin alerts."""

    @pytest.fixture
    def users(self):
        """Create multiple test users."""
        users = []
        for i in range(15):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                first_name=f"User{i}",
            )
            profile = LocalUserProfile.objects.create(
                user=user,
                password_hash="hashed_password",
            )
            profile.set_password("password123")
            profile.save()
            users.append((user, profile))
        return users

    @patch("api.tasks_lockout.send_admin_lockout_alert_task")
    @patch("api.tasks_lockout.get_ip_summary")
    @patch("api.tasks_lockout.get_affected_accounts")
    @patch("api.tasks_lockout.get_lockout_count")
    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.tasks_lockout.caches")
    def test_mass_lockout_triggers_admin_alert(
        self,
        mock_caches,
        mock_user_notification,
        mock_get_count,
        mock_get_accounts,
        mock_get_ip_summary,
        mock_admin_alert,
        users,
    ):
        """Test that mass lockout threshold triggers admin alert."""
        from api.tasks_lockout import check_mass_lockout_task

        # Setup mocks
        threshold = getattr(settings, "LOCKOUT_MASS_THRESHOLD", 10)
        lockout_count = 15  # Above threshold
        mock_get_count.return_value = lockout_count

        # Mock affected accounts data
        affected_accounts = [
            {
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "lockout_time": timezone.now().isoformat(),
            }
            for i in range(lockout_count)
        ]
        mock_get_accounts.return_value = affected_accounts

        # Mock IP summary
        ip_summary = [
            {"address": "192.168.1.100", "count": 10},
            {"address": "10.0.0.50", "count": 5},
        ]
        mock_get_ip_summary.return_value = ip_summary

        # Mock cache (no debounce key)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_caches.__getitem__.return_value = mock_cache

        # Mock the delay method
        mock_admin_alert.delay = MagicMock()

        # Create task instance with mock request
        task = check_mass_lockout_task
        mock_request = MagicMock()
        mock_request.id = "test-task-id"
        task.request = mock_request

        # Execute the task
        result = task()

        # Verify admin alert was triggered
        mock_admin_alert.delay.assert_called_once()
        call_kwargs = mock_admin_alert.delay.call_args[1]
        assert call_kwargs["lockout_count"] == lockout_count
        assert call_kwargs["time_window_minutes"] == settings.LOCKOUT_MASS_WINDOW_MINUTES
        assert call_kwargs["affected_accounts"] == affected_accounts
        assert call_kwargs["ip_summary"] == ip_summary

        # Verify debounce key was set
        mock_cache.set.assert_called_once()

        # Verify result indicates alert was triggered
        assert result["status"] == "alert_triggered"
        assert result["count"] == lockout_count
        assert result["threshold"] == threshold

    @patch("api.tasks_lockout.get_lockout_count")
    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    def test_below_threshold_no_admin_alert(
        self,
        mock_check_task,
        mock_user_notification,
        mock_get_count,
        users,
    ):
        """Test that lockouts below threshold don't trigger admin alert."""
        from api.tasks_lockout import check_mass_lockout_task

        # Setup mocks
        threshold = getattr(settings, "LOCKOUT_MASS_THRESHOLD", 10)
        lockout_count = 5  # Below threshold
        mock_get_count.return_value = lockout_count

        # Create task instance with mock request
        task = check_mass_lockout_task
        mock_request = MagicMock()
        mock_request.id = "test-task-id"
        task.request = mock_request

        # Execute the task
        result = task()

        # Verify result indicates below threshold
        assert result["status"] == "below_threshold"
        assert result["count"] == lockout_count
        assert result["threshold"] == threshold

    @patch("api.tasks_lockout.send_admin_lockout_alert_task")
    @patch("api.tasks_lockout.get_ip_summary")
    @patch("api.tasks_lockout.get_affected_accounts")
    @patch("api.tasks_lockout.get_lockout_count")
    @patch("api.tasks_lockout.caches")
    def test_debounce_prevents_duplicate_admin_alerts(
        self,
        mock_caches,
        mock_get_count,
        mock_get_accounts,
        mock_get_ip_summary,
        mock_admin_alert,
    ):
        """Test that debounce mechanism prevents duplicate admin alerts."""
        from api.tasks_lockout import check_mass_lockout_task

        # Setup mocks
        lockout_count = 15  # Above threshold
        mock_get_count.return_value = lockout_count

        # Mock cache with existing debounce key
        mock_cache = MagicMock()
        mock_cache.get.return_value = True  # Debounce key exists
        mock_caches.__getitem__.return_value = mock_cache

        # Create task instance with mock request
        task = check_mass_lockout_task
        mock_request = MagicMock()
        mock_request.id = "test-task-id"
        task.request = mock_request

        # Execute the task
        result = task()

        # Verify admin alert was NOT triggered (debounced)
        mock_admin_alert.delay.assert_not_called()

        # Verify debounce key was checked
        mock_cache.get.assert_called_once()

        # Verify cache.set was NOT called (alert already sent)
        mock_cache.set.assert_not_called()

        # Verify result indicates debounced
        assert result["status"] == "debounced"
        assert result["count"] == lockout_count


class TestLockoutFlowWithSettings:
    """Test lockout flow respects settings configuration."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="settingsuser",
            email="settings@example.com",
            first_name="Settings",
        )

    @pytest.fixture
    def local_profile(self, user):
        """Create a local user profile."""
        profile = LocalUserProfile.objects.create(
            user=user,
            password_hash="hashed_password",
        )
        profile.set_password("password123")
        profile.save()
        return profile

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_notifications_disabled_setting(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
        user,
        settings,
    ):
        """Test that LOCKOUT_NOTIFICATION_ENABLED=False prevents notifications."""
        settings.LOCKOUT_NOTIFICATION_ENABLED = False
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Trigger lockout
        for i in range(max_attempts):
            local_profile.record_login_attempt(success=False, ip_address="192.168.1.1")

        # Verify lockout occurred
        local_profile.refresh_from_db()
        assert local_profile.locked_until is not None

        # Verify notification task was NOT called (disabled)
        assert not mock_notification_task.delay.called

        # Verify audit log was still created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None

        # Verify mass tracking still occurred
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_successful_login_resets_counter(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
    ):
        """Test that successful login resets failed attempt counter."""
        # Record some failed attempts
        local_profile.record_login_attempt(success=False, ip_address="192.168.1.1")
        local_profile.record_login_attempt(success=False, ip_address="192.168.1.1")
        local_profile.record_login_attempt(success=False, ip_address="192.168.1.1")

        local_profile.refresh_from_db()
        assert local_profile.failed_login_attempts == 3

        # Successful login should reset counter
        local_profile.record_login_attempt(success=True, ip_address="192.168.1.1")

        local_profile.refresh_from_db()
        assert local_profile.failed_login_attempts == 0
        assert local_profile.locked_until is None

        # No notification should be sent (no lockout)
        assert not mock_notification_task.delay.called
        assert not mock_increment.called
        assert not mock_check_task.delay.called

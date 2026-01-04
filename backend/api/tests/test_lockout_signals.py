"""
Tests for lockout signal handlers and notification triggering.

Tests cover:
- django-axes signal handler (handle_user_locked_out)
- Local auth lockout integration (LocalUserProfile._send_lockout_notification)
- Notification task triggering
- Audit log creation
- Mass lockout tracking integration
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch, call

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from api.models import AuditLog
from api.models_local_auth import LocalUserProfile
from api.signals_lockout import handle_user_locked_out

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestAxesSignalHandler:
    """Tests for django-axes signal handler."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
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
    def test_signal_handler_with_valid_user(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user,
        mock_request,
    ):
        """Test signal handler with a valid user who has email."""
        mock_increment.return_value = 1

        # Simulate axes signal
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=user.username,
            ip_address="192.168.1.1",
        )

        # Verify notification task was called
        assert mock_notification_task.delay.called
        call_kwargs = mock_notification_task.delay.call_args[1]
        assert call_kwargs["user_email"] == user.email
        assert call_kwargs["user_data"]["first_name"] == user.first_name
        assert call_kwargs["user_data"]["username"] == user.username
        assert call_kwargs["lockout_data"]["ip_address"] == "192.168.1.1"
        assert call_kwargs["lockout_data"]["failure_count"] == settings.AXES_FAILURE_LIMIT
        assert "lockout_duration" in call_kwargs["lockout_data"]
        assert "unlock_time" in call_kwargs["lockout_data"]

        # Verify audit log was created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None
        assert audit_log.actor_id == str(user.id)
        assert audit_log.actor_email == user.email
        assert audit_log.metadata["ip_address"] == "192.168.1.1"
        assert audit_log.metadata["failure_count"] == settings.AXES_FAILURE_LIMIT
        assert audit_log.metadata["source"] == "django-axes"
        assert "unlock_time" in audit_log.metadata

        # Verify mass lockout tracking was incremented
        mock_increment.assert_called_once_with(
            username=user.username,
            email=user.email,
            ip_address="192.168.1.1",
            source="django-axes",
        )

        # Verify check_mass_lockout_task was triggered
        mock_check_task.delay.assert_called_once()

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_signal_handler_user_without_email(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        mock_request,
    ):
        """Test signal handler when user exists but has no email."""
        # Create user without email
        user = User.objects.create_user(
            username="noemail",
            email="",
        )
        mock_increment.return_value = 1

        # Simulate axes signal
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=user.username,
            ip_address="192.168.1.2",
        )

        # Notification should NOT be sent (no email)
        assert not mock_notification_task.delay.called

        # Audit log should still be created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None

        # Mass lockout tracking should still work
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_signal_handler_user_not_found(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        mock_request,
    ):
        """Test signal handler when user doesn't exist in database."""
        mock_increment.return_value = 1

        # Simulate axes signal with non-existent user
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username="nonexistent",
            ip_address="192.168.1.3",
        )

        # Notification should NOT be sent (no user)
        assert not mock_notification_task.delay.called

        # Audit log should still be created with username as fallback
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id="nonexistent",
        ).first()
        assert audit_log is not None
        assert audit_log.actor_id == "nonexistent"
        assert audit_log.metadata["source"] == "django-axes"

        # Mass lockout tracking should still work
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_signal_handler_notifications_disabled(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user,
        mock_request,
        settings,
    ):
        """Test signal handler when LOCKOUT_NOTIFICATION_ENABLED is False."""
        settings.LOCKOUT_NOTIFICATION_ENABLED = False
        mock_increment.return_value = 1

        # Simulate axes signal
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=user.username,
            ip_address="192.168.1.4",
        )

        # Notification should NOT be sent (disabled)
        assert not mock_notification_task.delay.called

        # Audit log should still be created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None

        # Mass lockout tracking should still work
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_signal_handler_mass_tracking_failure(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user,
        mock_request,
    ):
        """Test signal handler when mass lockout tracking fails."""
        # Simulate tracking failure
        mock_increment.side_effect = Exception("Redis connection failed")

        # Signal handler should not raise exception
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=user.username,
            ip_address="192.168.1.5",
        )

        # Notification should still be sent
        assert mock_notification_task.delay.called

        # Audit log should still be created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_signal_handler_lockout_data_format(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user,
        mock_request,
    ):
        """Test that lockout data is formatted correctly."""
        mock_increment.return_value = 1

        # Simulate axes signal
        handle_user_locked_out(
            sender=None,
            request=mock_request,
            username=user.username,
            ip_address="192.168.1.6",
        )

        # Verify lockout data format
        call_kwargs = mock_notification_task.delay.call_args[1]
        lockout_data = call_kwargs["lockout_data"]

        # Check duration format
        assert "hour" in lockout_data["lockout_duration"]
        assert str(settings.AXES_COOLOFF_TIME) in lockout_data["lockout_duration"]

        # Check failure count
        assert lockout_data["failure_count"] == settings.AXES_FAILURE_LIMIT

        # Check timestamps are present
        assert lockout_data["lockout_time"] is not None
        assert lockout_data["unlock_time"] is not None

        # Check reset password URL
        if hasattr(settings, "FRONTEND_URL"):
            assert lockout_data["reset_password_url"] is not None
            assert "reset-password" in lockout_data["reset_password_url"]


class TestLocalAuthLockoutIntegration:
    """Tests for local auth lockout integration."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
        )

    @pytest.fixture
    def local_profile(self, user):
        """Create a local user profile."""
        profile = LocalUserProfile.objects.create(
            user=user,
            password_hash="hashed_password",
        )
        return profile

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_record_login_attempt_triggers_lockout(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
    ):
        """Test that failed login attempts trigger lockout and notification."""
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Record failed attempts up to the limit
        for i in range(max_attempts):
            local_profile.record_login_attempt(
                success=False,
                ip_address="192.168.1.100"
            )

        # Verify profile is locked
        local_profile.refresh_from_db()
        assert local_profile.locked_until is not None
        assert local_profile.failed_login_attempts == max_attempts

        # Verify notification was sent
        assert mock_notification_task.delay.called
        call_kwargs = mock_notification_task.delay.call_args[1]
        assert call_kwargs["user_email"] == local_profile.user.email
        assert call_kwargs["user_data"]["username"] == local_profile.user.username
        assert call_kwargs["lockout_data"]["ip_address"] == "192.168.1.100"
        assert call_kwargs["lockout_data"]["failure_count"] == max_attempts

        # Verify audit log was created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(local_profile.user.id),
        ).first()
        assert audit_log is not None
        assert audit_log.metadata["source"] == "local-auth"
        assert audit_log.metadata["ip_address"] == "192.168.1.100"

        # Verify mass lockout tracking was incremented
        mock_increment.assert_called_once_with(
            username=local_profile.user.username,
            email=local_profile.user.email,
            ip_address="192.168.1.100",
            source="local-auth",
        )

        # Verify check_mass_lockout_task was triggered
        mock_check_task.delay.assert_called_once()

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_record_login_attempt_no_email(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
    ):
        """Test lockout when user has no email."""
        # Create user without email
        user = User.objects.create_user(
            username="noemail",
            email="",
        )
        profile = LocalUserProfile.objects.create(
            user=user,
            password_hash="hashed_password",
        )
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Record failed attempts up to the limit
        for i in range(max_attempts):
            profile.record_login_attempt(success=False, ip_address="192.168.1.101")

        # Notification should NOT be sent (no email)
        assert not mock_notification_task.delay.called

        # Audit log should still be created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(user.id),
        ).first()
        assert audit_log is not None

        # Mass lockout tracking should still work
        mock_increment.assert_called_once()
        mock_check_task.delay.assert_called_once()

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_record_login_attempt_notifications_disabled(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
        settings,
    ):
        """Test lockout when LOCKOUT_NOTIFICATION_ENABLED is False."""
        settings.LOCKOUT_NOTIFICATION_ENABLED = False
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Record failed attempts up to the limit
        for i in range(max_attempts):
            local_profile.record_login_attempt(
                success=False,
                ip_address="192.168.1.102"
            )

        # Notification should NOT be sent (disabled)
        assert not mock_notification_task.delay.called

        # Audit log should still be created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(local_profile.user.id),
        ).first()
        assert audit_log is not None

        # Mass lockout tracking should still work
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
        local_profile.record_login_attempt(success=False, ip_address="192.168.1.103")
        local_profile.record_login_attempt(success=False, ip_address="192.168.1.103")

        local_profile.refresh_from_db()
        assert local_profile.failed_login_attempts == 2

        # Successful login should reset counter
        local_profile.record_login_attempt(success=True, ip_address="192.168.1.103")

        local_profile.refresh_from_db()
        assert local_profile.failed_login_attempts == 0
        assert local_profile.locked_until is None

        # No notification should be sent (no lockout)
        assert not mock_notification_task.delay.called
        assert not mock_increment.called
        assert not mock_check_task.delay.called

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_lockout_duration_calculation(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
    ):
        """Test that lockout duration is calculated correctly."""
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Record failed attempts to trigger lockout
        for i in range(max_attempts):
            local_profile.record_login_attempt(success=False, ip_address="192.168.1.104")

        # Verify notification has correct duration format
        call_kwargs = mock_notification_task.delay.call_args[1]
        lockout_data = call_kwargs["lockout_data"]

        # Duration should be formatted as hours or minutes
        assert "lockout_duration" in lockout_data
        duration = lockout_data["lockout_duration"]
        assert "hour" in duration or "minute" in duration

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_lockout_tracking_failure_doesnt_block(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        local_profile,
    ):
        """Test that tracking failures don't prevent lockout."""
        # Simulate tracking failure
        mock_increment.side_effect = Exception("Redis connection failed")
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Lockout should still occur despite tracking failure
        for i in range(max_attempts):
            local_profile.record_login_attempt(success=False, ip_address="192.168.1.105")

        # Verify profile is still locked
        local_profile.refresh_from_db()
        assert local_profile.locked_until is not None

        # Notification should still be sent
        assert mock_notification_task.delay.called

        # Audit log should still be created
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
            resource_id=str(local_profile.user.id),
        ).first()
        assert audit_log is not None


class TestAuditLogCreation:
    """Tests specifically for audit log creation during lockouts."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
        )

    @patch("api.signals_lockout.send_lockout_notification_task")
    @patch("api.signals_lockout.check_mass_lockout_task")
    @patch("api.signals_lockout.increment_lockout_count")
    def test_audit_log_contains_all_required_fields(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
        user,
    ):
        """Test that audit log contains all required fields."""
        mock_increment.return_value = 1
        request = RequestFactory().get("/login")

        handle_user_locked_out(
            sender=None,
            request=request,
            username=user.username,
            ip_address="192.168.1.200",
        )

        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_type="User",
        ).first()

        assert audit_log is not None
        assert audit_log.action == "account_locked"
        assert audit_log.resource_type == "User"
        assert audit_log.resource_id == str(user.id)
        assert audit_log.actor_id == str(user.id)
        assert audit_log.actor_email == user.email

        # Check metadata
        assert "ip_address" in audit_log.metadata
        assert audit_log.metadata["ip_address"] == "192.168.1.200"
        assert "failure_count" in audit_log.metadata
        assert "lockout_duration_hours" in audit_log.metadata
        assert "unlock_time" in audit_log.metadata
        assert "source" in audit_log.metadata
        assert audit_log.metadata["source"] == "django-axes"

    @patch("api.models_local_auth.send_lockout_notification_task")
    @patch("api.models_local_auth.check_mass_lockout_task")
    @patch("api.models_local_auth.increment_lockout_count")
    def test_audit_log_distinguishes_source(
        self,
        mock_increment,
        mock_check_task,
        mock_notification_task,
    ):
        """Test that audit log correctly identifies source (axes vs local-auth)."""
        # Create user and profile
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
        )
        profile = LocalUserProfile.objects.create(
            user=user,
            password_hash="hashed_password",
        )
        mock_increment.return_value = 1
        max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)

        # Trigger local auth lockout
        for i in range(max_attempts):
            profile.record_login_attempt(success=False, ip_address="192.168.1.201")

        # Check audit log source
        audit_log = AuditLog.objects.filter(
            action="account_locked",
            resource_id=str(user.id),
        ).first()

        assert audit_log is not None
        assert audit_log.metadata["source"] == "local-auth"

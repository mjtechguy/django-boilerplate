"""
Tests for lockout notification Celery tasks.

Tests cover:
- send_lockout_notification_task: User lockout email notifications
- send_admin_lockout_alert_task: Admin mass lockout alerts
- check_mass_lockout_task: Mass lockout detection and threshold checking
- Task configuration (retries, reliability settings)
- Debounce behavior for admin alerts
"""

from unittest.mock import MagicMock, patch, call

import pytest
from django.conf import settings
from django.utils import timezone

from api.tasks_lockout import (
    send_lockout_notification_task,
    send_admin_lockout_alert_task,
    check_mass_lockout_task,
)


class TestSendLockoutNotificationTask:
    """Tests for send_lockout_notification_task."""

    @pytest.fixture
    def user_email(self):
        """Test user email."""
        return "test@example.com"

    @pytest.fixture
    def user_data(self):
        """Test user data."""
        return {
            "first_name": "Test",
            "email": "test@example.com",
            "username": "testuser",
        }

    @pytest.fixture
    def lockout_data(self):
        """Test lockout data."""
        return {
            "lockout_duration": "1 hour",
            "failure_count": 5,
            "ip_address": "192.168.1.100",
            "lockout_time": timezone.now().isoformat(),
            "unlock_time": (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
            "reset_password_url": "https://example.com/reset",
        }

    @pytest.fixture
    def mock_request(self):
        """Mock Celery request object."""
        request = MagicMock()
        request.id = "test-task-id-123"
        return request

    @patch("api.tasks_lockout.send_email")
    def test_successful_email_sent(
        self, mock_send_email, user_email, user_data, lockout_data, mock_request
    ):
        """Test that user notification email is sent successfully."""
        # Mock successful email sending
        mock_send_email.return_value = {"success": True}

        # Create task instance with mock request
        task = send_lockout_notification_task
        task.request = mock_request

        # Call the task
        result = task(user_email, user_data, lockout_data)

        # Verify send_email was called with correct parameters
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args

        assert call_args.kwargs["to"] == [user_email]
        assert call_args.kwargs["subject"] == "Account Temporarily Locked - Security Alert"
        assert call_args.kwargs["template"] == "email/account_lockout.html"

        # Verify context includes user data and lockout data
        context = call_args.kwargs["context"]
        assert context["user"] == user_data
        assert context["lockout_duration"] == lockout_data["lockout_duration"]
        assert context["failure_count"] == lockout_data["failure_count"]
        assert context["ip_address"] == lockout_data["ip_address"]

        # Verify return value
        assert result["status"] == "success"
        assert result["user_email"] == user_email
        assert result["task_id"] == "test-task-id-123"

    @patch("api.tasks_lockout.send_email")
    def test_email_sending_failure(
        self, mock_send_email, user_email, user_data, lockout_data, mock_request
    ):
        """Test handling of email sending failure."""
        # Mock failed email sending
        mock_send_email.return_value = {
            "success": False,
            "error": "SMTP connection failed",
        }

        # Create task instance with mock request
        task = send_lockout_notification_task
        task.request = mock_request

        # Call the task
        result = task(user_email, user_data, lockout_data)

        # Verify send_email was called
        mock_send_email.assert_called_once()

        # Verify return value indicates failure
        assert result["status"] == "failed"
        assert result["user_email"] == user_email
        assert result["result"]["success"] is False
        assert result["result"]["error"] == "SMTP connection failed"

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_NOTIFICATION_ENABLED", False)
    def test_notifications_disabled(
        self, mock_send_email, user_email, user_data, lockout_data, mock_request
    ):
        """Test that notification is skipped when disabled in settings."""
        # Create task instance with mock request
        task = send_lockout_notification_task
        task.request = mock_request

        # Call the task
        result = task(user_email, user_data, lockout_data)

        # Verify send_email was NOT called
        mock_send_email.assert_not_called()

        # Verify return value indicates disabled
        assert result["status"] == "disabled"
        assert result["task_id"] == "test-task-id-123"

    @patch("api.tasks_lockout.send_email")
    def test_context_merging(
        self, mock_send_email, user_email, user_data, lockout_data, mock_request
    ):
        """Test that user data and lockout data are properly merged in context."""
        mock_send_email.return_value = {"success": True}

        task = send_lockout_notification_task
        task.request = mock_request

        result = task(user_email, user_data, lockout_data)

        # Get the context that was passed to send_email
        context = mock_send_email.call_args.kwargs["context"]

        # Verify user data is in context
        assert context["user"] == user_data

        # Verify all lockout data fields are in context (spread)
        assert context["lockout_duration"] == lockout_data["lockout_duration"]
        assert context["failure_count"] == lockout_data["failure_count"]
        assert context["ip_address"] == lockout_data["ip_address"]
        assert context["lockout_time"] == lockout_data["lockout_time"]
        assert context["unlock_time"] == lockout_data["unlock_time"]
        assert context["reset_password_url"] == lockout_data["reset_password_url"]

    def test_task_has_retry_config(self):
        """Test that task has proper retry configuration."""
        task = send_lockout_notification_task

        assert task.autoretry_for == (Exception,)
        assert task.retry_backoff is True
        assert task.max_retries == 3

    def test_task_has_reliability_config(self):
        """Test that task has reliability settings."""
        task = send_lockout_notification_task

        assert task.acks_late is True


class TestSendAdminLockoutAlertTask:
    """Tests for send_admin_lockout_alert_task."""

    @pytest.fixture
    def affected_accounts(self):
        """Test affected accounts data."""
        return [
            {
                "username": "user1",
                "email": "user1@example.com",
                "lockout_time": timezone.now().isoformat(),
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "lockout_time": timezone.now().isoformat(),
            },
            {
                "username": "user3",
                "email": "user3@example.com",
                "lockout_time": timezone.now().isoformat(),
            },
        ]

    @pytest.fixture
    def ip_summary(self):
        """Test IP summary data."""
        return [
            {"address": "192.168.1.100", "count": 5},
            {"address": "10.0.0.50", "count": 3},
        ]

    @pytest.fixture
    def mock_request(self):
        """Mock Celery request object."""
        request = MagicMock()
        request.id = "test-admin-task-id-456"
        return request

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_ADMIN_EMAILS", ["admin@example.com", "security@example.com"])
    def test_successful_admin_alert_sent(
        self, mock_send_email, affected_accounts, ip_summary, mock_request
    ):
        """Test that admin alert email is sent successfully."""
        mock_send_email.return_value = {"success": True}

        task = send_admin_lockout_alert_task
        task.request = mock_request

        result = task(
            lockout_count=10,
            time_window_minutes=5,
            affected_accounts=affected_accounts,
            ip_summary=ip_summary,
        )

        # Verify send_email was called
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args

        # Verify recipients
        assert call_args.kwargs["to"] == ["admin@example.com", "security@example.com"]

        # Verify subject includes lockout count
        assert "10 Accounts Affected" in call_args.kwargs["subject"]

        # Verify template
        assert call_args.kwargs["template"] == "email/mass_lockout_alert.html"

        # Verify context
        context = call_args.kwargs["context"]
        assert context["lockout_count"] == 10
        assert context["time_window"] == 5
        assert context["affected_accounts"] == affected_accounts
        assert context["ip_summary"] == ip_summary
        assert "detection_time" in context
        assert "threshold" in context

        # Verify return value
        assert result["status"] == "success"
        assert result["lockout_count"] == 10
        assert result["admin_count"] == 2
        assert result["task_id"] == "test-admin-task-id-456"

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_ADMIN_EMAILS", [])
    def test_no_admin_emails_configured(
        self, mock_send_email, affected_accounts, ip_summary, mock_request
    ):
        """Test that alert is skipped when no admin emails are configured."""
        task = send_admin_lockout_alert_task
        task.request = mock_request

        result = task(
            lockout_count=10,
            time_window_minutes=5,
            affected_accounts=affected_accounts,
            ip_summary=ip_summary,
        )

        # Verify send_email was NOT called
        mock_send_email.assert_not_called()

        # Verify return value indicates skipped
        assert result["status"] == "skipped"
        assert result["reason"] == "No admin emails configured"
        assert result["task_id"] == "test-admin-task-id-456"

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_NOTIFICATION_ENABLED", False)
    @patch.object(settings, "LOCKOUT_ADMIN_EMAILS", ["admin@example.com"])
    def test_notifications_disabled(
        self, mock_send_email, affected_accounts, ip_summary, mock_request
    ):
        """Test that alert is skipped when notifications are disabled."""
        task = send_admin_lockout_alert_task
        task.request = mock_request

        result = task(
            lockout_count=10,
            time_window_minutes=5,
            affected_accounts=affected_accounts,
            ip_summary=ip_summary,
        )

        # Verify send_email was NOT called
        mock_send_email.assert_not_called()

        # Verify return value indicates disabled
        assert result["status"] == "disabled"
        assert result["task_id"] == "test-admin-task-id-456"

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_ADMIN_EMAILS", ["admin@example.com"])
    def test_email_sending_failure(
        self, mock_send_email, affected_accounts, ip_summary, mock_request
    ):
        """Test handling of admin alert email sending failure."""
        mock_send_email.return_value = {
            "success": False,
            "error": "Email server unavailable",
        }

        task = send_admin_lockout_alert_task
        task.request = mock_request

        result = task(
            lockout_count=10,
            time_window_minutes=5,
            affected_accounts=affected_accounts,
            ip_summary=ip_summary,
        )

        # Verify send_email was called
        mock_send_email.assert_called_once()

        # Verify return value indicates failure
        assert result["status"] == "failed"
        assert result["lockout_count"] == 10
        assert result["result"]["success"] is False
        assert result["result"]["error"] == "Email server unavailable"

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_ADMIN_EMAILS", ["admin@example.com"])
    @patch.object(settings, "LOCKOUT_MASS_THRESHOLD", 10)
    def test_context_includes_threshold(
        self, mock_send_email, affected_accounts, ip_summary, mock_request
    ):
        """Test that context includes the mass lockout threshold setting."""
        mock_send_email.return_value = {"success": True}

        task = send_admin_lockout_alert_task
        task.request = mock_request

        result = task(
            lockout_count=15,
            time_window_minutes=5,
            affected_accounts=affected_accounts,
            ip_summary=ip_summary,
        )

        # Get context passed to send_email
        context = mock_send_email.call_args.kwargs["context"]

        # Verify threshold is included
        assert context["threshold"] == 10

    @patch("api.tasks_lockout.send_email")
    @patch.object(settings, "LOCKOUT_ADMIN_EMAILS", ["admin@example.com"])
    def test_ip_summary_optional(
        self, mock_send_email, affected_accounts, mock_request
    ):
        """Test that IP summary is optional (can be None)."""
        mock_send_email.return_value = {"success": True}

        task = send_admin_lockout_alert_task
        task.request = mock_request

        # Call without ip_summary parameter
        result = task(
            lockout_count=10,
            time_window_minutes=5,
            affected_accounts=affected_accounts,
        )

        # Verify send_email was still called successfully
        mock_send_email.assert_called_once()

        # Verify context has ip_summary as None
        context = mock_send_email.call_args.kwargs["context"]
        assert context["ip_summary"] is None

    def test_task_has_retry_config(self):
        """Test that task has proper retry configuration."""
        task = send_admin_lockout_alert_task

        assert task.autoretry_for == (Exception,)
        assert task.retry_backoff is True
        assert task.max_retries == 3

    def test_task_has_reliability_config(self):
        """Test that task has reliability settings."""
        task = send_admin_lockout_alert_task

        assert task.acks_late is True


class TestCheckMassLockoutTask:
    """Tests for check_mass_lockout_task."""

    @pytest.fixture
    def mock_request(self):
        """Mock Celery request object."""
        request = MagicMock()
        request.id = "test-check-task-id-789"
        return request

    @pytest.fixture
    def mock_cache(self):
        """Mock Django cache."""
        cache = MagicMock()
        cache.get.return_value = None  # No debounce key by default
        return cache

    @patch("api.tasks_lockout.get_lockout_count")
    @patch.object(settings, "LOCKOUT_MASS_THRESHOLD", 10)
    @patch.object(settings, "LOCKOUT_MASS_WINDOW_MINUTES", 5)
    def test_below_threshold(self, mock_get_count, mock_request):
        """Test when lockout count is below threshold."""
        # Mock count below threshold
        mock_get_count.return_value = 5

        task = check_mass_lockout_task
        task.request = mock_request

        result = task()

        # Verify get_lockout_count was called
        mock_get_count.assert_called_once_with(5)

        # Verify result indicates below threshold
        assert result["status"] == "below_threshold"
        assert result["count"] == 5
        assert result["threshold"] == 10
        assert result["task_id"] == "test-check-task-id-789"

    @patch("api.tasks_lockout.send_admin_lockout_alert_task")
    @patch("api.tasks_lockout.get_ip_summary")
    @patch("api.tasks_lockout.get_affected_accounts")
    @patch("api.tasks_lockout.get_lockout_count")
    @patch("api.tasks_lockout.caches")
    @patch.object(settings, "LOCKOUT_MASS_THRESHOLD", 10)
    @patch.object(settings, "LOCKOUT_MASS_WINDOW_MINUTES", 5)
    def test_threshold_exceeded_triggers_alert(
        self,
        mock_caches,
        mock_get_count,
        mock_get_accounts,
        mock_get_ip_summary,
        mock_alert_task,
        mock_request,
    ):
        """Test that admin alert is triggered when threshold is exceeded."""
        # Mock count above threshold
        mock_get_count.return_value = 15

        # Mock affected accounts data
        mock_get_accounts.return_value = [
            {"username": "user1", "email": "user1@example.com"},
            {"username": "user2", "email": "user2@example.com"},
        ]

        # Mock IP summary data
        mock_get_ip_summary.return_value = [
            {"address": "192.168.1.100", "count": 10},
        ]

        # Mock cache (no debounce key)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_caches.__getitem__.return_value = mock_cache

        # Mock the delay method
        mock_alert_task.delay = MagicMock()

        task = check_mass_lockout_task
        task.request = mock_request

        result = task()

        # Verify tracking functions were called
        mock_get_count.assert_called_once_with(5)
        mock_get_accounts.assert_called_once_with(5)
        mock_get_ip_summary.assert_called_once_with(5)

        # Verify debounce key was checked and set
        mock_cache.get.assert_called_once_with("mass_lockout_alert_sent:5m")
        mock_cache.set.assert_called_once_with("mass_lockout_alert_sent:5m", True, 300)

        # Verify admin alert task was triggered
        mock_alert_task.delay.assert_called_once_with(
            lockout_count=15,
            time_window_minutes=5,
            affected_accounts=mock_get_accounts.return_value,
            ip_summary=mock_get_ip_summary.return_value,
        )

        # Verify result
        assert result["status"] == "alert_triggered"
        assert result["count"] == 15
        assert result["threshold"] == 10
        assert result["affected_accounts_count"] == 2
        assert result["unique_ips"] == 1

    @patch("api.tasks_lockout.get_lockout_count")
    @patch("api.tasks_lockout.caches")
    @patch.object(settings, "LOCKOUT_MASS_THRESHOLD", 10)
    @patch.object(settings, "LOCKOUT_MASS_WINDOW_MINUTES", 5)
    def test_debounce_prevents_duplicate_alerts(
        self, mock_caches, mock_get_count, mock_request
    ):
        """Test that debounce key prevents duplicate admin alerts."""
        # Mock count above threshold
        mock_get_count.return_value = 15

        # Mock cache with existing debounce key
        mock_cache = MagicMock()
        mock_cache.get.return_value = True  # Debounce key exists
        mock_caches.__getitem__.return_value = mock_cache

        task = check_mass_lockout_task
        task.request = mock_request

        result = task()

        # Verify debounce key was checked
        mock_cache.get.assert_called_once_with("mass_lockout_alert_sent:5m")

        # Verify cache.set was NOT called (alert already sent)
        mock_cache.set.assert_not_called()

        # Verify result indicates debounced
        assert result["status"] == "debounced"
        assert result["count"] == 15
        assert result["threshold"] == 10

    @patch("api.tasks_lockout.get_lockout_count")
    @patch.object(settings, "LOCKOUT_NOTIFICATION_ENABLED", False)
    def test_notifications_disabled(self, mock_get_count, mock_request):
        """Test that check is skipped when notifications are disabled."""
        task = check_mass_lockout_task
        task.request = mock_request

        result = task()

        # Verify get_lockout_count was NOT called
        mock_get_count.assert_not_called()

        # Verify result indicates disabled
        assert result["status"] == "disabled"
        assert result["task_id"] == "test-check-task-id-789"

    @patch("api.tasks_lockout.send_admin_lockout_alert_task")
    @patch("api.tasks_lockout.get_ip_summary")
    @patch("api.tasks_lockout.get_affected_accounts")
    @patch("api.tasks_lockout.get_lockout_count")
    @patch("api.tasks_lockout.caches")
    @patch.object(settings, "LOCKOUT_MASS_THRESHOLD", 10)
    @patch.object(settings, "LOCKOUT_MASS_WINDOW_MINUTES", 5)
    def test_debounce_ttl_matches_window(
        self,
        mock_caches,
        mock_get_count,
        mock_get_accounts,
        mock_get_ip_summary,
        mock_alert_task,
        mock_request,
    ):
        """Test that debounce key TTL matches the time window."""
        mock_get_count.return_value = 15
        mock_get_accounts.return_value = []
        mock_get_ip_summary.return_value = []

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_caches.__getitem__.return_value = mock_cache

        mock_alert_task.delay = MagicMock()

        task = check_mass_lockout_task
        task.request = mock_request

        result = task()

        # Verify debounce key TTL is 5 minutes = 300 seconds
        mock_cache.set.assert_called_once_with("mass_lockout_alert_sent:5m", True, 300)

    def test_task_has_retry_config(self):
        """Test that task has proper retry configuration."""
        task = check_mass_lockout_task

        assert task.autoretry_for == (Exception,)
        assert task.retry_backoff is True
        assert task.max_retries == 3

    def test_task_has_reliability_config(self):
        """Test that task has reliability settings."""
        task = check_mass_lockout_task

        assert task.acks_late is True


class TestTaskRegistration:
    """Tests to verify tasks are properly registered."""

    def test_tasks_are_importable(self):
        """All lockout tasks should be importable."""
        from api.tasks_lockout import (
            send_lockout_notification_task,
            send_admin_lockout_alert_task,
            check_mass_lockout_task,
        )

        assert send_lockout_notification_task is not None
        assert send_admin_lockout_alert_task is not None
        assert check_mass_lockout_task is not None

    def test_tasks_are_shared_tasks(self):
        """Tasks should be Celery shared_tasks."""
        # Celery tasks have a 'name' attribute
        assert hasattr(send_lockout_notification_task, "name")
        assert hasattr(send_admin_lockout_alert_task, "name")
        assert hasattr(check_mass_lockout_task, "name")

        # Task names should include the task name
        assert "send_lockout_notification_task" in send_lockout_notification_task.name
        assert "send_admin_lockout_alert_task" in send_admin_lockout_alert_task.name
        assert "check_mass_lockout_task" in check_mass_lockout_task.name

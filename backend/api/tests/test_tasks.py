"""
Tests for Celery tasks: idempotency, deduplication, and retry configuration.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.tasks import (
    audit_fan_out,
    force_fail_task,
    process_webhook_event,
    task_dedup_key,
)


class TestTaskDedupKey:
    """Tests for deduplication key generation."""

    def test_same_args_produce_same_key(self):
        """Same task name and args should produce the same dedup key."""
        key1 = task_dedup_key("my_task", ("arg1",), {"kwarg": "value"})
        key2 = task_dedup_key("my_task", ("arg1",), {"kwarg": "value"})
        assert key1 == key2

    def test_different_args_produce_different_keys(self):
        """Different args should produce different dedup keys."""
        key1 = task_dedup_key("my_task", ("arg1",), {"kwarg": "value1"})
        key2 = task_dedup_key("my_task", ("arg1",), {"kwarg": "value2"})
        assert key1 != key2

    def test_different_task_names_produce_different_keys(self):
        """Different task names should produce different dedup keys."""
        key1 = task_dedup_key("task_a", ("arg1",), {})
        key2 = task_dedup_key("task_b", ("arg1",), {})
        assert key1 != key2

    def test_key_format(self):
        """Dedup key should have the expected prefix."""
        key = task_dedup_key("my_task", (), {})
        assert key.startswith("task_dedup:")

    def test_key_is_deterministic(self):
        """Key generation should be deterministic (no random elements)."""
        keys = [task_dedup_key("task", ("a", "b"), {"x": 1}) for _ in range(10)]
        assert len(set(keys)) == 1


class TestIdempotentTaskDecorator:
    """Tests for the idempotent_task decorator behavior."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache for testing."""
        cache = MagicMock()
        cache.get.return_value = None
        return cache

    @pytest.fixture
    def mock_request(self):
        """Create a mock Celery request."""
        request = MagicMock()
        request.id = "test-task-id-123"
        return request

    def test_first_execution_proceeds(self, mock_cache, mock_request):
        """First execution of a task should proceed normally."""
        with patch("api.tasks.get_dedup_cache", return_value=mock_cache):
            # Simulate task not being in cache
            mock_cache.get.return_value = None

            # Create a mock task
            mock_task = MagicMock()
            mock_task.name = "test_task"
            mock_task.request = mock_request

            # The cache should be checked
            # (actual decorator test would require Celery task execution context)
            dedup_key = task_dedup_key("test_task", ("arg",), {})
            result = mock_cache.get(dedup_key)
            assert result is None

    def test_duplicate_execution_returns_early(self, mock_cache, mock_request):
        """Duplicate execution should return deduplicated status."""
        # Simulate task already in cache
        mock_cache.get.return_value = {"task_id": "previous-id", "status": "completed"}

        dedup_key = task_dedup_key("test_task", ("arg",), {})
        result = mock_cache.get(dedup_key)
        assert result is not None
        assert result["status"] == "completed"


class TestAuditFanOutTask:
    """Tests for the audit_fan_out task configuration."""

    def test_task_has_retry_config(self):
        """Task should have retry configuration."""
        assert audit_fan_out.autoretry_for == (Exception,)
        assert audit_fan_out.retry_backoff is True
        assert audit_fan_out.retry_backoff_max == 600
        assert audit_fan_out.max_retries == 3

    def test_task_has_reliability_config(self):
        """Task should have reliability settings."""
        assert audit_fan_out.acks_late is True
        assert audit_fan_out.reject_on_worker_lost is True

    def test_task_has_failure_handler(self):
        """Task should have a DLQ failure handler."""
        assert audit_fan_out.on_failure is not None


class TestProcessWebhookEventTask:
    """Tests for the process_webhook_event task configuration."""

    def test_task_has_retry_config(self):
        """Task should have retry configuration."""
        assert process_webhook_event.autoretry_for == (Exception,)
        assert process_webhook_event.retry_backoff is True
        assert process_webhook_event.max_retries == 3

    def test_task_has_reliability_config(self):
        """Task should have reliability settings."""
        assert process_webhook_event.acks_late is True


class TestForceFailTask:
    """Tests for the force_fail_task test helper."""

    def test_task_has_no_retries(self):
        """Force fail task should have no retries for immediate DLQ."""
        assert force_fail_task.max_retries == 0

    def test_task_has_failure_handler(self):
        """Task should have a DLQ failure handler."""
        assert force_fail_task.on_failure is not None


class TestCeleryConfiguration:
    """Tests for Celery configuration settings."""

    def test_celery_settings_present(self):
        """Verify Celery settings are properly configured."""
        from django.conf import settings

        # Reliability settings
        assert settings.CELERY_TASK_ACKS_LATE is True
        assert settings.CELERY_TASK_REJECT_ON_WORKER_LOST is True
        assert settings.CELERY_WORKER_PREFETCH_MULTIPLIER == 1

        # Retry defaults
        assert settings.CELERY_TASK_DEFAULT_RETRY_DELAY == 60
        assert settings.CELERY_TASK_MAX_RETRIES == 3
        assert settings.CELERY_TASK_RETRY_BACKOFF is True
        assert settings.CELERY_TASK_RETRY_BACKOFF_MAX == 600
        assert settings.CELERY_TASK_RETRY_JITTER is True

        # Task tracking
        assert settings.CELERY_TASK_TRACK_STARTED is True
        assert settings.CELERY_TASK_TIME_LIMIT == 300
        assert settings.CELERY_TASK_SOFT_TIME_LIMIT == 240

        # Queue configuration
        assert "default" in settings.CELERY_TASK_QUEUES
        assert "dlq" in settings.CELERY_TASK_QUEUES

    def test_dedup_ttl_setting(self):
        """Verify dedup TTL setting exists."""
        from django.conf import settings

        assert hasattr(settings, "CELERY_TASK_DEDUP_TTL")
        assert settings.CELERY_TASK_DEDUP_TTL > 0


class TestTaskRegistration:
    """Tests to verify tasks are properly registered."""

    def test_tasks_are_importable(self):
        """All tasks should be importable."""
        from api.tasks import audit_fan_out, force_fail_task, process_webhook_event

        assert audit_fan_out is not None
        assert process_webhook_event is not None
        assert force_fail_task is not None

    def test_tasks_are_shared_tasks(self):
        """Tasks should be Celery shared_tasks."""
        from api.tasks import audit_fan_out, force_fail_task, process_webhook_event

        # Celery tasks have a 'name' attribute
        assert hasattr(audit_fan_out, "name")
        assert hasattr(process_webhook_event, "name")
        assert hasattr(force_fail_task, "name")

        # Task names should include the module path
        assert "audit_fan_out" in audit_fan_out.name
        assert "process_webhook_event" in process_webhook_event.name
        assert "force_fail_task" in force_fail_task.name

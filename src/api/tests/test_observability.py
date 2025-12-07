"""
Tests for observability: structured logging, PII redaction, metrics, and health checks.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from config.logging import (
    add_request_context,
    add_service_info,
    pii_redactor,
    redact_dict,
    redact_value,
)
from config.observability import (
    MetricsCollector,
    bind_context,
    clear_request_context,
    get_request_context,
    log_audit_decision,
    set_request_context,
)


class TestPIIRedaction(TestCase):
    """Tests for PII redaction functionality."""

    def test_redact_value_by_field_name(self):
        """Test redaction based on field name."""
        # Email field
        self.assertEqual(redact_value("test@example.com", "email"), "[REDACTED]")
        self.assertEqual(redact_value("test@example.com", "user_email"), "[REDACTED]")

        # Password field
        self.assertEqual(redact_value("secret123", "password"), "[REDACTED]")

        # Token field
        self.assertEqual(redact_value("abc123token", "token"), "[REDACTED]")
        self.assertEqual(redact_value("abc123", "api_token"), "[REDACTED]")

        # API key field
        self.assertEqual(redact_value("key-123", "api_key"), "[REDACTED]")
        self.assertEqual(redact_value("key-123", "apikey"), "[REDACTED]")

    def test_redact_value_preserves_non_pii(self):
        """Test that non-PII values are preserved."""
        self.assertEqual(redact_value("hello", "message"), "hello")
        self.assertEqual(redact_value("12345", "user_id"), "12345")
        self.assertEqual(redact_value("active", "status"), "active")

    def test_redact_value_email_pattern(self):
        """Test email pattern detection in values."""
        result = redact_value("Contact: user@example.com for help", "message")
        self.assertEqual(result, "Contact: [EMAIL_REDACTED] for help")

    def test_redact_value_ssn_pattern(self):
        """Test SSN pattern detection in values."""
        result = redact_value("SSN: 123-45-6789", "message")
        self.assertEqual(result, "SSN: [SSN_REDACTED]")

        result = redact_value("SSN: 123.45.6789", "message")
        self.assertEqual(result, "SSN: [SSN_REDACTED]")

    def test_redact_value_credit_card_pattern(self):
        """Test credit card pattern detection in values."""
        result = redact_value("Card: 1234-5678-9012-3456", "message")
        self.assertEqual(result, "Card: [CARD_REDACTED]")

        result = redact_value("Card: 1234 5678 9012 3456", "message")
        self.assertEqual(result, "Card: [CARD_REDACTED]")

    def test_redact_dict(self):
        """Test recursive dictionary redaction."""
        data = {
            "user_email": "test@example.com",
            "username": "johndoe",
            "nested": {
                "password": "secret123",
                "role": "admin",
            },
            "items": [
                {"token": "abc123"},
                {"name": "item1"},
            ],
        }

        result = redact_dict(data)

        self.assertEqual(result["user_email"], "[REDACTED]")
        self.assertEqual(result["username"], "johndoe")
        self.assertEqual(result["nested"]["password"], "[REDACTED]")
        self.assertEqual(result["nested"]["role"], "admin")
        self.assertEqual(result["items"][0]["token"], "[REDACTED]")
        self.assertEqual(result["items"][1]["name"], "item1")

    def test_redact_dict_max_depth(self):
        """Test that max depth is respected."""
        deep_data = {
            "level1": {
                "level2": {"level3": {"level4": {"level5": {"level6": {"password": "secret"}}}}}
            }
        }
        result = redact_dict(deep_data, max_depth=3)
        # After max depth, should not redact deeper levels
        self.assertIn("level4", result["level1"]["level2"]["level3"])


class TestPIIRedactorProcessor(TestCase):
    """Tests for the structlog PII redactor processor."""

    def test_pii_redactor_masks_pii_fields(self):
        """Test that PII fields are masked in log events."""
        event_dict = {
            "event": "test_event",
            "email": "test@example.com",
            "password": "secret123",
            "username": "johndoe",
        }

        result = pii_redactor(None, "info", event_dict)

        self.assertEqual(result["email"], "[REDACTED]")
        self.assertEqual(result["password"], "[REDACTED]")
        self.assertEqual(result["username"], "johndoe")

    @override_settings(AUDIT_PII_POLICY="drop")
    def test_pii_redactor_drops_pii_fields(self):
        """Test that PII fields are dropped when policy is 'drop'."""
        event_dict = {
            "event": "test_event",
            "email": "test@example.com",
            "password": "secret123",
            "username": "johndoe",
        }

        result = pii_redactor(None, "info", event_dict)

        self.assertNotIn("email", result)
        self.assertNotIn("password", result)
        self.assertEqual(result["username"], "johndoe")

    def test_pii_redactor_preserves_core_fields(self):
        """Test that core log fields are preserved."""
        event_dict = {
            "event": "test_event",
            "message": "Hello",
            "timestamp": "2024-01-01T00:00:00Z",
            "level": "info",
        }

        result = pii_redactor(None, "info", event_dict)

        self.assertEqual(result["event"], "test_event")
        self.assertEqual(result["message"], "Hello")
        self.assertEqual(result["timestamp"], "2024-01-01T00:00:00Z")
        self.assertEqual(result["level"], "info")


class TestRequestContext(TestCase):
    """Tests for request context management."""

    def setUp(self):
        """Clear context before each test."""
        clear_request_context()

    def tearDown(self):
        """Clear context after each test."""
        clear_request_context()

    def test_set_and_get_request_context(self):
        """Test setting and getting request context."""
        set_request_context(
            request_id="req-123",
            trace_id="trace-456",
            actor="user-1",
            org_id="org-1",
            path="/api/v1/test",
            method="GET",
        )

        context = get_request_context()

        self.assertEqual(context["request_id"], "req-123")
        self.assertEqual(context["trace_id"], "trace-456")
        self.assertEqual(context["actor"], "user-1")
        self.assertEqual(context["org_id"], "org-1")
        self.assertEqual(context["path"], "/api/v1/test")
        self.assertEqual(context["method"], "GET")

    def test_set_request_context_filters_empty_values(self):
        """Test that empty values are filtered from context."""
        set_request_context(
            request_id="req-123",
            trace_id="",
            actor="",
            org_id="org-1",
        )

        context = get_request_context()

        self.assertIn("request_id", context)
        # trace_id defaults to request_id when empty, so it's present
        self.assertEqual(context["trace_id"], "req-123")
        self.assertNotIn("actor", context)  # Empty, should be filtered
        self.assertIn("org_id", context)

    def test_trace_id_defaults_to_request_id(self):
        """Test that trace_id defaults to request_id if empty."""
        set_request_context(request_id="req-123")

        context = get_request_context()

        self.assertEqual(context["trace_id"], "req-123")

    def test_bind_context_adds_fields(self):
        """Test binding additional context fields."""
        set_request_context(request_id="req-123")
        bind_context(custom_field="custom_value")

        context = get_request_context()

        self.assertEqual(context["request_id"], "req-123")
        self.assertEqual(context["custom_field"], "custom_value")

    def test_clear_request_context(self):
        """Test clearing request context."""
        set_request_context(request_id="req-123", actor="user-1")
        clear_request_context()

        context = get_request_context()

        self.assertEqual(context, {})


class TestAddRequestContextProcessor(TestCase):
    """Tests for the add_request_context structlog processor."""

    def setUp(self):
        """Clear context before each test."""
        clear_request_context()

    def tearDown(self):
        """Clear context after each test."""
        clear_request_context()

    def test_add_request_context_adds_fields(self):
        """Test that request context is added to log events."""
        set_request_context(request_id="req-123", actor="user-1")

        event_dict = {"event": "test"}
        result = add_request_context(None, "info", event_dict)

        self.assertEqual(result["request_id"], "req-123")
        self.assertEqual(result["actor"], "user-1")

    def test_add_request_context_when_empty(self):
        """Test processor when context is empty."""
        event_dict = {"event": "test"}
        result = add_request_context(None, "info", event_dict)

        self.assertEqual(result, {"event": "test"})


class TestAddServiceInfoProcessor(TestCase):
    """Tests for the add_service_info structlog processor."""

    @override_settings(ENVIRONMENT="production")
    def test_add_service_info(self):
        """Test that service info is added to log events."""
        event_dict = {"event": "test"}
        result = add_service_info(None, "info", event_dict)

        self.assertEqual(result["service"], "django-api")
        self.assertEqual(result["environment"], "production")


class TestMetricsCollector(TestCase):
    """Tests for the metrics collector."""

    def setUp(self):
        """Create a fresh metrics collector for each test."""
        self.metrics = MetricsCollector()

    def test_increment_counter(self):
        """Test incrementing a counter."""
        self.metrics.inc("test_counter")
        self.metrics.inc("test_counter")
        self.metrics.inc("test_counter", 5)

        self.assertEqual(self.metrics.counters["test_counter"], 7)

    def test_counter_with_labels(self):
        """Test counter with labels."""
        self.metrics.inc("http_requests", labels={"method": "GET", "status": "200"})
        self.metrics.inc("http_requests", labels={"method": "POST", "status": "201"})

        self.assertEqual(self.metrics.counters['http_requests{method="GET",status="200"}'], 1)
        self.assertEqual(self.metrics.counters['http_requests{method="POST",status="201"}'], 1)

    def test_observe_histogram(self):
        """Test observing histogram values."""
        self.metrics.observe("request_duration", 0.1)
        self.metrics.observe("request_duration", 0.2)
        self.metrics.observe("request_duration", 0.3)

        values = self.metrics.histograms["request_duration"]
        self.assertEqual(len(values), 3)
        self.assertAlmostEqual(sum(values), 0.6)

    def test_histogram_limits_observations(self):
        """Test that histogram limits observations to 1000."""
        for i in range(1100):
            self.metrics.observe("test_hist", float(i))

        self.assertEqual(len(self.metrics.histograms["test_hist"]), 1000)

    def test_set_gauge(self):
        """Test setting gauge values."""
        self.metrics.set_gauge("active_connections", 10)
        self.assertEqual(self.metrics.gauges["active_connections"], 10)

        self.metrics.set_gauge("active_connections", 15)
        self.assertEqual(self.metrics.gauges["active_connections"], 15)

    def test_get_metrics(self):
        """Test getting all metrics as dictionary."""
        self.metrics.inc("counter1")
        self.metrics.observe("hist1", 0.5)
        self.metrics.set_gauge("gauge1", 100)

        result = self.metrics.get_metrics()

        self.assertIn("counters", result)
        self.assertIn("histograms", result)
        self.assertIn("gauges", result)
        self.assertEqual(result["counters"]["counter1"], 1)
        self.assertEqual(result["gauges"]["gauge1"], 100)

    def test_to_prometheus_format(self):
        """Test Prometheus format export."""
        self.metrics.inc("http_requests_total", labels={"method": "GET"})
        self.metrics.observe("http_request_duration_seconds", 0.5)
        self.metrics.set_gauge("active_connections", 10)

        output = self.metrics.to_prometheus_format()

        self.assertIn("# TYPE http_requests_total counter", output)
        self.assertIn("http_requests_total", output)
        self.assertIn("# TYPE http_request_duration_seconds histogram", output)
        self.assertIn("http_request_duration_seconds_count", output)
        self.assertIn("# TYPE active_connections gauge", output)
        self.assertIn("active_connections 10", output)


class TestAuditLogging(TestCase):
    """Tests for audit logging functionality."""

    def setUp(self):
        """Set up request context."""
        set_request_context(
            request_id="req-123",
            actor="user-1",
            org_id="org-1",
        )

    def tearDown(self):
        """Clear context."""
        clear_request_context()

    @patch("config.observability.logger")
    def test_log_audit_decision(self, mock_logger):
        """Test logging authorization decisions."""
        log_audit_decision(
            action="read",
            resource_kind="document",
            resource_id="doc-123",
            result="allow",
            policy_version="1.0.0",
            decision_id="dec-456",
            decision_time_ms=5.2,
        )

        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args[1]

        self.assertEqual(call_kwargs["action"], "read")
        self.assertEqual(call_kwargs["resource_kind"], "document")
        self.assertEqual(call_kwargs["resource_id"], "doc-123")
        self.assertEqual(call_kwargs["result"], "allow")
        self.assertEqual(call_kwargs["policy_version"], "1.0.0")
        self.assertEqual(call_kwargs["decision_id"], "dec-456")
        self.assertEqual(call_kwargs["actor"], "user-1")
        self.assertEqual(call_kwargs["org_id"], "org-1")


class TestHealthEndpoints(TestCase):
    """Tests for health check endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_liveness_endpoint(self):
        """Test liveness probe returns 200."""
        response = self.client.get("/api/v1/health/live")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "alive")

    @patch("api.views_monitoring.connection")
    @patch("api.views_monitoring.caches")
    def test_readiness_endpoint_healthy(self, mock_caches, mock_connection):
        """Test readiness probe when all services are healthy."""
        # Mock database
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Mock cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = "ok"
        mock_caches.__getitem__.return_value = mock_cache

        response = self.client.get("/api/v1/health/ready")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["checks"]["database"]["status"], "ready")
        self.assertEqual(data["checks"]["cache"]["status"], "ready")

    @patch("api.views_monitoring.connection")
    @patch("api.views_monitoring.caches")
    def test_readiness_endpoint_database_down(self, mock_caches, mock_connection):
        """Test readiness probe when database is down."""
        # Mock database failure
        mock_connection.cursor.side_effect = Exception("Connection refused")

        # Mock cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = "ok"
        mock_caches.__getitem__.return_value = mock_cache

        response = self.client.get("/api/v1/health/ready")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertEqual(data["status"], "not_ready")
        self.assertEqual(data["checks"]["database"]["status"], "not_ready")


class TestPrometheusMetricsEndpoint(TestCase):
    """Tests for Prometheus metrics endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_prometheus_metrics_endpoint(self):
        """Test that Prometheus metrics endpoint returns text format."""
        response = self.client.get("/api/v1/monitoring/metrics")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/plain", response["Content-Type"])

    def test_app_metrics_json_endpoint(self):
        """Test that app metrics endpoint returns JSON."""
        response = self.client.get("/api/v1/monitoring/metrics/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("counters", data)
        self.assertIn("histograms", data)
        self.assertIn("gauges", data)

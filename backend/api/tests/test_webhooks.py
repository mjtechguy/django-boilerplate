"""
Tests for webhook delivery system.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import WebhookDelivery, WebhookEndpoint
from api.tasks import deliver_webhook
from api.webhooks import dispatch_webhook, generate_webhook_secret, sign_payload, verify_signature


class TestWebhookModels(TestCase):
    """Tests for webhook models."""

    def test_create_webhook_endpoint(self):
        """Test creating a webhook endpoint."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
            events=["user.created", "org.updated"],
        )

        assert endpoint.id is not None
        assert endpoint.org_id == "org-123"
        assert endpoint.name == "Test Webhook"
        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.secret == "test-secret"
        assert endpoint.events == ["user.created", "org.updated"]
        assert endpoint.is_active is True
        assert endpoint.headers == {}

    def test_webhook_endpoint_str(self):
        """Test webhook endpoint string representation."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
        )
        assert str(endpoint) == "WebhookEndpoint<Test Webhook>"

    def test_create_webhook_delivery(self):
        """Test creating a webhook delivery record."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123", "email": "test@example.com"},
        )

        assert delivery.id is not None
        assert delivery.endpoint == endpoint
        assert delivery.event_type == "user.created"
        assert delivery.payload == {"user_id": "123", "email": "test@example.com"}
        assert delivery.status == WebhookDelivery.Status.PENDING
        assert delivery.attempts == 0
        assert delivery.last_attempt_at is None

    def test_webhook_delivery_str(self):
        """Test webhook delivery string representation."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        assert str(delivery) == "WebhookDelivery<user.created -> Test Webhook>"


class TestWebhookSignatures:
    """Tests for webhook signature generation and verification."""

    def test_generate_webhook_secret(self):
        """Test webhook secret generation."""
        secret = generate_webhook_secret()
        assert isinstance(secret, str)
        assert len(secret) > 20  # Should be a reasonably long secret

    def test_generate_unique_secrets(self):
        """Test that generated secrets are unique."""
        secret1 = generate_webhook_secret()
        secret2 = generate_webhook_secret()
        assert secret1 != secret2

    def test_sign_payload(self):
        """Test payload signing."""
        payload = {"event": "test", "data": {"id": 123}}
        secret = "test-secret"
        timestamp = 1234567890

        signature = sign_payload(payload, secret, timestamp)

        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_sign_payload_deterministic(self):
        """Test that signing is deterministic."""
        payload = {"event": "test", "data": {"id": 123}}
        secret = "test-secret"
        timestamp = 1234567890

        sig1 = sign_payload(payload, secret, timestamp)
        sig2 = sign_payload(payload, secret, timestamp)

        assert sig1 == sig2

    def test_sign_payload_different_secret(self):
        """Test that different secrets produce different signatures."""
        payload = {"event": "test"}
        timestamp = 1234567890

        sig1 = sign_payload(payload, "secret1", timestamp)
        sig2 = sign_payload(payload, "secret2", timestamp)

        assert sig1 != sig2

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        payload = {"event": "test", "data": {"id": 123}}
        secret = "test-secret"
        timestamp = 1234567890

        signature = sign_payload(payload, secret, timestamp)
        is_valid = verify_signature(payload, secret, timestamp, signature)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        payload = {"event": "test"}
        secret = "test-secret"
        timestamp = 1234567890

        is_valid = verify_signature(payload, secret, timestamp, "sha256=invalid")

        assert is_valid is False

    def test_verify_signature_wrong_secret(self):
        """Test signature verification with wrong secret."""
        payload = {"event": "test"}
        timestamp = 1234567890

        signature = sign_payload(payload, "secret1", timestamp)
        is_valid = verify_signature(payload, "secret2", timestamp, signature)

        assert is_valid is False


@pytest.mark.django_db
class TestWebhookDispatch:
    """Tests for webhook dispatch logic."""

    @patch("api.tasks.deliver_webhook")
    def test_dispatch_webhook_creates_delivery(self, mock_task):
        """Test that dispatching a webhook creates delivery records."""
        mock_task.delay = MagicMock()

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            events=["user.created"],
            is_active=True,
        )

        payload = {"user_id": "123", "email": "test@example.com"}
        delivery_ids = dispatch_webhook("user.created", payload, org_id="org-123")

        assert len(delivery_ids) == 1
        assert WebhookDelivery.objects.count() == 1

        delivery = WebhookDelivery.objects.first()
        assert delivery.endpoint == endpoint
        assert delivery.event_type == "user.created"
        assert delivery.payload == payload
        assert delivery.status == WebhookDelivery.Status.PENDING

    @patch("api.tasks.deliver_webhook")
    def test_dispatch_webhook_queues_task(self, mock_task):
        """Test that dispatching a webhook queues a Celery task."""
        mock_task.delay = MagicMock()

        WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            events=["user.created"],
            is_active=True,
        )

        payload = {"user_id": "123"}
        dispatch_webhook("user.created", payload, org_id="org-123")

        assert mock_task.delay.called

    @patch("api.tasks.deliver_webhook")
    def test_dispatch_webhook_inactive_endpoint(self, mock_task):
        """Test that inactive endpoints are not triggered."""
        mock_task.delay = MagicMock()

        WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Inactive Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            events=["user.created"],
            is_active=False,
        )

        payload = {"user_id": "123"}
        delivery_ids = dispatch_webhook("user.created", payload, org_id="org-123")

        assert len(delivery_ids) == 0
        assert WebhookDelivery.objects.count() == 0
        assert not mock_task.delay.called

    @patch("api.tasks.deliver_webhook")
    def test_dispatch_webhook_wrong_event(self, mock_task):
        """Test that endpoints not subscribed to an event are not triggered."""
        mock_task.delay = MagicMock()

        WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            events=["org.updated"],  # Not subscribed to user.created
            is_active=True,
        )

        payload = {"user_id": "123"}
        delivery_ids = dispatch_webhook("user.created", payload, org_id="org-123")

        assert len(delivery_ids) == 0
        assert WebhookDelivery.objects.count() == 0

    @patch("api.tasks.deliver_webhook")
    def test_dispatch_webhook_empty_events_list(self, mock_task):
        """Test that endpoints with empty events list receive all events."""
        mock_task.delay = MagicMock()

        WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            events=[],  # Empty list means subscribe to all
            is_active=True,
        )

        payload = {"user_id": "123"}
        delivery_ids = dispatch_webhook("any.event", payload, org_id="org-123")

        assert len(delivery_ids) == 1
        assert WebhookDelivery.objects.count() == 1


@pytest.mark.django_db
class TestDeliverWebhookTask:
    """Tests for the deliver_webhook Celery task."""

    @patch("requests.post")
    def test_deliver_webhook_success(self, mock_post):
        """Test successful webhook delivery."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Create endpoint and delivery
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result
        assert result["status"] == "delivered"
        assert result["response_status"] == 200

        # Verify delivery was updated
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.DELIVERED
        assert delivery.attempts == 1
        assert delivery.response_status == 200
        assert delivery.last_attempt_at is not None

        # Verify request was made with correct headers
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"] == {"user_id": "123"}
        assert "X-Webhook-Signature" in call_kwargs["headers"]
        assert "X-Webhook-Timestamp" in call_kwargs["headers"]
        assert "X-Webhook-Event" in call_kwargs["headers"]
        assert call_kwargs["headers"]["X-Webhook-Event"] == "user.created"

    @patch("requests.post")
    def test_deliver_webhook_failure_status(self, mock_post):
        """Test webhook delivery with error status code."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # Create endpoint and delivery
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result
        assert result["status"] == "failed"
        assert result["response_status"] == 500

        # Verify delivery was updated
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert delivery.attempts == 1
        assert delivery.response_status == 500

    @patch("requests.post")
    def test_deliver_webhook_inactive_endpoint(self, mock_post):
        """Test that inactive endpoints are skipped."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            is_active=False,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result
        assert result["status"] == "skipped"
        assert not mock_post.called

        # Verify delivery was updated
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED

    @patch("requests.post")
    def test_deliver_webhook_custom_headers(self, mock_post):
        """Test webhook delivery with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            is_active=True,
            headers={"X-Custom-Header": "custom-value"},
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        deliver_webhook(str(delivery.id))

        # Verify custom header was included
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["X-Custom-Header"] == "custom-value"


@pytest.mark.django_db
class TestWebhookSSRFProtection:
    """Tests for SSRF protection in webhook delivery."""

    @patch("api.ssrf.resolve_hostname")
    def test_deliver_webhook_blocks_private_ip(self, mock_resolve):
        """Test that webhook delivery fails for private IP URLs."""
        # Mock DNS resolution to return a private IP
        mock_resolve.return_value = ["192.168.1.100"]

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Evil Endpoint",
            url="https://evil.example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result indicates failure
        assert result["status"] == "failed"
        assert "SSRF" in result["error"]

        # Verify delivery status was updated to FAILED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert "SSRF Protection" in delivery.response_body
        assert "192.168.1.100" in delivery.response_body

    @patch("api.ssrf.resolve_hostname")
    def test_deliver_webhook_blocks_localhost(self, mock_resolve):
        """Test that webhook delivery fails for localhost URLs."""
        # Mock DNS resolution to return localhost IP
        mock_resolve.return_value = ["127.0.0.1"]

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Localhost Endpoint",
            url="https://malicious.example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result indicates failure
        assert result["status"] == "failed"
        assert "SSRF" in result["error"]

        # Verify delivery status was updated to FAILED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert "SSRF Protection" in delivery.response_body
        assert "127.0.0.1" in delivery.response_body

    @patch("api.ssrf.resolve_hostname")
    def test_deliver_webhook_blocks_metadata_endpoint(self, mock_resolve):
        """Test that webhook delivery fails for cloud metadata endpoint URLs."""
        # Mock DNS resolution to return AWS/Azure/GCP metadata IP
        mock_resolve.return_value = ["169.254.169.254"]

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Metadata Endpoint",
            url="https://attacker.example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result indicates failure
        assert result["status"] == "failed"
        assert "SSRF" in result["error"]

        # Verify delivery status was updated to FAILED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert "SSRF Protection" in delivery.response_body
        assert "169.254.169.254" in delivery.response_body

    @patch("api.ssrf.resolve_hostname")
    @patch("requests.request")
    def test_deliver_webhook_succeeds_for_valid_public_url(self, mock_request, mock_resolve):
        """Test that webhook delivery succeeds for valid public URLs."""
        # Mock DNS resolution to return a public IP
        mock_resolve.return_value = ["93.184.216.34"]

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_request.return_value = mock_response

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Valid Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result indicates success
        assert result["status"] == "delivered"
        assert result["response_status"] == 200

        # Verify delivery status was updated to DELIVERED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.DELIVERED
        assert delivery.response_status == 200
        assert delivery.response_body == "OK"

        # Verify request was made to the resolved IP (DNS rebinding protection)
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        # The URL should be to the IP address, not the hostname
        assert "93.184.216.34" in mock_request.call_args[1]["url"]
        # But the Host header should be the original hostname
        assert call_kwargs["headers"]["Host"] == "example.com"

    @patch("api.ssrf.resolve_hostname")
    @patch("structlog.get_logger")
    def test_deliver_webhook_logs_ssrf_attempts(self, mock_get_logger, mock_resolve):
        """Test that SSRF attempts are properly logged with security_event flag."""
        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock DNS resolution to return a private IP
        mock_resolve.return_value = ["10.0.0.1"]

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Evil Endpoint",
            url="https://evil.example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        deliver_webhook(str(delivery.id))

        # Verify security event was logged
        # Look for error log call with security_event=True
        error_calls = [
            call
            for call in mock_logger.error.call_args_list
            if len(call[0]) > 0 and "ssrf" in call[0][0].lower()
        ]

        assert len(error_calls) > 0, "Expected security event to be logged"

        # Check that security_event flag was set in one of the calls
        security_logged = False
        for call in mock_logger.error.call_args_list:
            if len(call) > 1 and "security_event" in call[1]:
                if call[1]["security_event"] is True:
                    security_logged = True
                    break

        assert security_logged, "Expected security_event=True in log call"

    @patch("api.ssrf.resolve_hostname")
    def test_deliver_webhook_ssrf_sets_failed_status(self, mock_resolve):
        """Test that delivery status is correctly set to FAILED for SSRF violations."""
        # Mock DNS resolution to return multiple private IPs
        mock_resolve.return_value = ["172.16.0.1", "172.16.0.2"]

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Internal Endpoint",
            url="https://internal.example.com/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Verify initial status is PENDING
        assert delivery.status == WebhookDelivery.Status.PENDING
        assert delivery.attempts == 0

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result
        assert result["status"] == "failed"
        assert "SSRF" in result["error"]
        assert result["attempts"] == 1

        # Verify delivery record was updated
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert delivery.attempts == 1
        assert delivery.last_attempt_at is not None
        assert "SSRF Protection" in delivery.response_body
        assert delivery.response_status is None  # No HTTP response received

    def test_deliver_webhook_blocks_localhost_hostname_directly(self):
        """Test that localhost hostname is blocked directly without DNS resolution."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Localhost Direct",
            url="https://localhost/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result indicates failure
        assert result["status"] == "failed"
        assert "SSRF" in result["error"]

        # Verify delivery status was updated to FAILED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert "localhost" in delivery.response_body.lower()

    def test_deliver_webhook_blocks_metadata_hostname_directly(self):
        """Test that metadata hostname is blocked directly without DNS resolution."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Metadata Direct",
            url="https://metadata.google.internal/webhook",
            secret="test-secret",
            is_active=True,
        )

        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )

        # Execute task
        result = deliver_webhook(str(delivery.id))

        # Verify result indicates failure
        assert result["status"] == "failed"
        assert "SSRF" in result["error"]

        # Verify delivery status was updated to FAILED
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.Status.FAILED
        assert "metadata" in delivery.response_body.lower()


@pytest.mark.django_db
class TestWebhookAPI:
    """Tests for webhook REST API endpoints.

    Webhook endpoints require platform_admin authentication.
    """

    @pytest.fixture(autouse=True)
    def setup_auth(self, monkeypatch):
        """Setup authenticated client with platform_admin role."""
        self.client = APIClient()

        # Mock platform admin claims
        platform_admin_claims = {
            "sub": "platform-admin-user",
            "email": "admin@example.com",
            "realm_access": {"roles": ["platform_admin"]},
        }

        def mock_validate(self_auth, token):
            return platform_admin_claims

        monkeypatch.setattr(
            "api.auth.KeycloakJWTAuthentication._validate_token", mock_validate
        )

        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

    def test_list_webhook_endpoints(self):
        """Test listing webhook endpoints."""
        WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Endpoint 1",
            url="https://example.com/webhook1",
            secret="secret1",
        )
        WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Endpoint 2",
            url="https://example.com/webhook2",
            secret="secret2",
        )

        response = self.client.get("/api/v1/webhooks")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    def test_create_webhook_endpoint(self):
        """Test creating a webhook endpoint."""
        data = {
            "org_id": "org-123",
            "name": "New Endpoint",
            "url": "https://example.com/webhook",
            "events": ["user.created", "org.updated"],
        }

        response = self.client.post("/api/v1/webhooks", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert WebhookEndpoint.objects.count() == 1

        endpoint = WebhookEndpoint.objects.first()
        assert endpoint.name == "New Endpoint"
        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.events == ["user.created", "org.updated"]
        assert endpoint.secret  # Should be auto-generated
        assert "secret" not in response.json()  # Secret should not be in response

    def test_get_webhook_endpoint_detail(self):
        """Test getting webhook endpoint details."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret-12345678",
        )

        response = self.client.get(f"/api/v1/webhooks/{endpoint.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Endpoint"
        assert data["url"] == "https://example.com/webhook"
        # Secret should be masked
        assert "test" in data["secret"]
        assert "..." in data["secret"]

    def test_update_webhook_endpoint(self):
        """Test updating a webhook endpoint."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Old Name",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        data = {"name": "New Name"}
        response = self.client.patch(f"/api/v1/webhooks/{endpoint.id}", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        endpoint.refresh_from_db()
        assert endpoint.name == "New Name"

    def test_delete_webhook_endpoint(self):
        """Test deleting a webhook endpoint."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        response = self.client.delete(f"/api/v1/webhooks/{endpoint.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert WebhookEndpoint.objects.count() == 0

    @patch("api.views_webhooks.dispatch_webhook")
    def test_webhook_test_endpoint(self, mock_dispatch):
        """Test the webhook test endpoint."""
        mock_dispatch.return_value = ["delivery-id-123"]

        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        response = self.client.post(f"/api/v1/webhooks/{endpoint.id}/test")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "delivery_ids" in data
        assert data["delivery_ids"] == ["delivery-id-123"]
        assert mock_dispatch.called

    def test_list_webhook_deliveries(self):
        """Test listing deliveries for a webhook endpoint."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="user.created",
            payload={"user_id": "123"},
        )
        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="org.updated",
            payload={"org_id": "456"},
        )

        response = self.client.get(f"/api/v1/webhooks/{endpoint.id}/deliveries")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    def test_create_webhook_with_private_ip_url_fails(self):
        """Test that creating a webhook with private IP URL fails with 400."""
        data = {
            "org_id": "org-123",
            "name": "Private IP Endpoint",
            "url": "https://192.168.1.100/webhook",
            "events": ["user.created"],
        }

        response = self.client.post("/api/v1/webhooks", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.json()
        assert WebhookEndpoint.objects.count() == 0

    def test_create_webhook_with_localhost_url_fails(self):
        """Test that creating a webhook with localhost URL fails with 400."""
        data = {
            "org_id": "org-123",
            "name": "Localhost Endpoint",
            "url": "https://localhost/webhook",
            "events": ["user.created"],
        }

        response = self.client.post("/api/v1/webhooks", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.json()
        error_message = str(response.json()["url"])
        assert "localhost" in error_message.lower() or "blocked" in error_message.lower()
        assert WebhookEndpoint.objects.count() == 0

    def test_create_webhook_with_metadata_endpoint_fails(self):
        """Test that creating a webhook with metadata endpoint URL fails with 400."""
        data = {
            "org_id": "org-123",
            "name": "Metadata Endpoint",
            "url": "https://169.254.169.254/latest/meta-data/",
            "events": ["user.created"],
        }

        response = self.client.post("/api/v1/webhooks", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.json()
        error_message = str(response.json()["url"])
        assert "169.254.169.254" in error_message or "metadata" in error_message.lower()
        assert WebhookEndpoint.objects.count() == 0

    def test_create_webhook_with_internal_network_url_fails(self):
        """Test that creating a webhook with internal network URL fails with 400."""
        data = {
            "org_id": "org-123",
            "name": "Internal Endpoint",
            "url": "https://10.0.0.5/webhook",
            "events": ["user.created"],
        }

        response = self.client.post("/api/v1/webhooks", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.json()
        error_message = str(response.json()["url"])
        assert "10.0.0.5" in error_message or "private" in error_message.lower()
        assert WebhookEndpoint.objects.count() == 0

    def test_create_webhook_with_valid_url_succeeds(self):
        """Test that creating a webhook with valid public URL succeeds."""
        data = {
            "org_id": "org-123",
            "name": "Valid Endpoint",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }

        response = self.client.post("/api/v1/webhooks", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert WebhookEndpoint.objects.count() == 1
        endpoint = WebhookEndpoint.objects.first()
        assert endpoint.url == "https://example.com/webhook"

    def test_update_webhook_url_to_private_ip_fails(self):
        """Test that updating webhook URL to private IP fails with 400."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        data = {"url": "https://192.168.1.1/webhook"}
        response = self.client.patch(f"/api/v1/webhooks/{endpoint.id}", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.json()
        error_message = str(response.json()["url"])
        assert "192.168.1.1" in error_message or "private" in error_message.lower()

        # Verify URL was not updated
        endpoint.refresh_from_db()
        assert endpoint.url == "https://example.com/webhook"

    def test_update_webhook_url_to_localhost_fails(self):
        """Test that updating webhook URL to localhost fails with 400."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        data = {"url": "https://127.0.0.1/webhook"}
        response = self.client.patch(f"/api/v1/webhooks/{endpoint.id}", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "url" in response.json()
        error_message = str(response.json()["url"])
        assert "127.0.0.1" in error_message or "loopback" in error_message.lower()

        # Verify URL was not updated
        endpoint.refresh_from_db()
        assert endpoint.url == "https://example.com/webhook"

    def test_update_webhook_url_to_valid_url_succeeds(self):
        """Test that updating webhook URL to valid public URL succeeds."""
        endpoint = WebhookEndpoint.objects.create(
            org_id="org-123",
            name="Test Endpoint",
            url="https://example.com/webhook",
            secret="test-secret",
        )

        data = {"url": "https://newdomain.com/webhook"}
        response = self.client.patch(f"/api/v1/webhooks/{endpoint.id}", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        endpoint.refresh_from_db()
        assert endpoint.url == "https://newdomain.com/webhook"

    def test_ssrf_validation_error_messages_are_user_friendly(self):
        """Test that SSRF validation errors return clear, user-friendly messages."""
        test_cases = [
            {
                "url": "https://192.168.1.100/webhook",
                "expected_keywords": ["192.168.1.100", "private"],
            },
            {
                "url": "https://localhost/webhook",
                "expected_keywords": ["localhost", "blocked"],
            },
            {
                "url": "https://10.0.0.1/webhook",
                "expected_keywords": ["10.0.0.1", "private"],
            },
        ]

        for test_case in test_cases:
            data = {
                "org_id": "org-123",
                "name": "Test Endpoint",
                "url": test_case["url"],
                "events": ["user.created"],
            }

            response = self.client.post("/api/v1/webhooks", data, format="json")

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "url" in response.json()
            error_message = str(response.json()["url"]).lower()

            # Check that at least one expected keyword is in the error message
            assert any(
                keyword.lower() in error_message for keyword in test_case["expected_keywords"]
            ), f"Expected one of {test_case['expected_keywords']} in error message: {error_message}"

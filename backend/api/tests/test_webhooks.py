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
class TestWebhookAPI:
    """Tests for webhook REST API endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = APIClient()

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

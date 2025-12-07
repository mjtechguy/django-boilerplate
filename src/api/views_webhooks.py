"""
REST API views for webhook management.
"""

import structlog
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import WebhookDelivery, WebhookEndpoint
from api.serializers_webhooks import (
    WebhookDeliverySerializer,
    WebhookEndpointDetailSerializer,
    WebhookEndpointSerializer,
)
from api.webhooks import dispatch_webhook

logger = structlog.get_logger(__name__)


class WebhookEndpointListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/webhooks - List all webhook endpoints
    POST /api/v1/webhooks - Create a new webhook endpoint
    """

    permission_classes = [AllowAny]
    serializer_class = WebhookEndpointSerializer
    queryset = WebhookEndpoint.objects.all()

    def get_queryset(self):
        """Filter by org_id if provided."""
        queryset = super().get_queryset()
        org_id = self.request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(org_id=org_id)
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        """Log webhook endpoint creation."""
        instance = serializer.save()
        logger.info(
            "webhook_endpoint_created",
            endpoint_id=str(instance.id),
            org_id=instance.org_id,
            name=instance.name,
            url=instance.url,
            events=instance.events,
        )


class WebhookEndpointDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/v1/webhooks/{id} - Get webhook endpoint details
    PATCH /api/v1/webhooks/{id} - Update webhook endpoint
    DELETE /api/v1/webhooks/{id} - Delete webhook endpoint
    """

    permission_classes = [AllowAny]
    serializer_class = WebhookEndpointDetailSerializer
    queryset = WebhookEndpoint.objects.all()
    lookup_field = "pk"

    def perform_update(self, serializer):
        """Log webhook endpoint update."""
        instance = serializer.save()
        logger.info(
            "webhook_endpoint_updated",
            endpoint_id=str(instance.id),
            org_id=instance.org_id,
            name=instance.name,
        )

    def perform_destroy(self, instance):
        """Log webhook endpoint deletion."""
        logger.info(
            "webhook_endpoint_deleted",
            endpoint_id=str(instance.id),
            org_id=instance.org_id,
            name=instance.name,
        )
        instance.delete()


class WebhookDeliveryListView(generics.ListAPIView):
    """
    GET /api/v1/webhooks/{id}/deliveries - List deliveries for a webhook endpoint
    """

    permission_classes = [AllowAny]
    serializer_class = WebhookDeliverySerializer

    def get_queryset(self):
        """Get deliveries for the specified endpoint."""
        endpoint_id = self.kwargs.get("pk")
        return WebhookDelivery.objects.filter(endpoint_id=endpoint_id).order_by("-created_at")


class WebhookTestView(APIView):
    """
    POST /api/v1/webhooks/{id}/test - Send a test webhook event
    """

    permission_classes = [AllowAny]

    def post(self, request, pk):
        """Send a test webhook to the specified endpoint."""
        try:
            endpoint = WebhookEndpoint.objects.get(pk=pk)
        except WebhookEndpoint.DoesNotExist:
            return Response(
                {"error": "Webhook endpoint not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create a test payload
        test_payload = {
            "event": "webhook.test",
            "message": "This is a test webhook delivery",
            "endpoint_id": str(endpoint.id),
            "endpoint_name": endpoint.name,
        }

        logger.info(
            "webhook_test_triggered",
            endpoint_id=str(endpoint.id),
            org_id=endpoint.org_id,
        )

        # Dispatch the test webhook
        delivery_ids = dispatch_webhook(
            event_type="webhook.test",
            payload=test_payload,
            org_id=endpoint.org_id,
        )

        return Response(
            {
                "message": "Test webhook queued for delivery",
                "delivery_ids": delivery_ids,
            },
            status=status.HTTP_200_OK,
        )

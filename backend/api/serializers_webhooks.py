"""
Serializers for webhook endpoints and deliveries.
"""

from rest_framework import serializers

from api.models import WebhookDelivery, WebhookEndpoint
from api.webhooks import generate_webhook_secret


class WebhookEndpointSerializer(serializers.ModelSerializer):
    """Serializer for WebhookEndpoint model."""

    secret = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "org_id",
            "name",
            "url",
            "secret",
            "events",
            "is_active",
            "headers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        """Auto-generate secret if not provided."""
        if "secret" not in validated_data or not validated_data["secret"]:
            validated_data["secret"] = generate_webhook_secret()
        return super().create(validated_data)

    def to_representation(self, instance):
        """Hide secret in responses."""
        representation = super().to_representation(instance)
        # Remove secret from response entirely
        if "secret" in representation:
            del representation["secret"]
        return representation


class WebhookEndpointDetailSerializer(serializers.ModelSerializer):
    """Extended serializer that includes masked secret for detail view."""

    secret = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "org_id",
            "name",
            "url",
            "secret",
            "events",
            "is_active",
            "headers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_secret(self, obj):
        """Return masked secret."""
        if obj.secret:
            # Show first 4 and last 4 characters
            if len(obj.secret) > 8:
                return f"{obj.secret[:4]}...{obj.secret[-4:]}"
            return "***"
        return None


class WebhookDeliverySerializer(serializers.ModelSerializer):
    """Serializer for WebhookDelivery model (read-only)."""

    endpoint_name = serializers.CharField(source="endpoint.name", read_only=True)
    endpoint_url = serializers.CharField(source="endpoint.url", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "endpoint",
            "endpoint_name",
            "endpoint_url",
            "event_type",
            "payload",
            "status",
            "attempts",
            "last_attempt_at",
            "response_status",
            "response_body",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "endpoint",
            "endpoint_name",
            "endpoint_url",
            "event_type",
            "payload",
            "status",
            "attempts",
            "last_attempt_at",
            "response_status",
            "response_body",
            "created_at",
            "updated_at",
        ]

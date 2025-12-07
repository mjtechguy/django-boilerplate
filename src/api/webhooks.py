"""
Webhook delivery system for outbound webhooks.
"""

import hashlib
import hmac
import json
import secrets

import structlog

logger = structlog.get_logger(__name__)


def generate_webhook_secret() -> str:
    """Generate a secure webhook secret for signing payloads."""
    return secrets.token_urlsafe(32)


def sign_payload(payload: dict, secret: str, timestamp: int) -> str:
    """
    Sign a webhook payload using HMAC-SHA256.

    Args:
        payload: The webhook payload dictionary
        secret: The webhook secret key
        timestamp: Unix timestamp for the signature

    Returns:
        Signature string in format "sha256=<hex_digest>"
    """
    message = f"{timestamp}.{json.dumps(payload, sort_keys=True)}"
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: dict, secret: str, timestamp: int, received_signature: str) -> bool:
    """
    Verify a webhook signature.

    Args:
        payload: The webhook payload dictionary
        secret: The webhook secret key
        timestamp: Unix timestamp from the signature
        received_signature: The signature to verify

    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = sign_payload(payload, secret, timestamp)
    return hmac.compare_digest(expected_signature, received_signature)


def dispatch_webhook(event_type: str, payload: dict, org_id: str = None) -> list[str]:
    """
    Dispatch a webhook event to all matching endpoints.

    This function finds all active webhook endpoints that are subscribed to the given
    event type and creates delivery records for them. The actual delivery is handled
    asynchronously by the deliver_webhook Celery task.

    Args:
        event_type: The type of event (e.g., "user.created", "org.updated")
        payload: The event payload data
        org_id: Optional organization ID to scope webhook endpoints

    Returns:
        List of delivery IDs (UUIDs as strings) that were created
    """
    from api.models import WebhookDelivery, WebhookEndpoint
    from api.tasks import deliver_webhook

    logger.info(
        "webhook_dispatch_start",
        event_type=event_type,
        org_id=org_id,
        payload_keys=list(payload.keys()),
    )

    # Find matching active endpoints
    endpoints_query = WebhookEndpoint.objects.filter(is_active=True)

    if org_id:
        endpoints_query = endpoints_query.filter(org_id=org_id)

    # Filter endpoints that have this event in their subscribed events
    # or have an empty events list (subscribe to all)
    matching_endpoints = []
    for endpoint in endpoints_query:
        if not endpoint.events or event_type in endpoint.events:
            matching_endpoints.append(endpoint)

    logger.info(
        "webhook_endpoints_matched",
        event_type=event_type,
        org_id=org_id,
        endpoint_count=len(matching_endpoints),
    )

    delivery_ids = []
    for endpoint in matching_endpoints:
        # Create a delivery record
        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload=payload,
            status=WebhookDelivery.Status.PENDING,
        )

        delivery_ids.append(str(delivery.id))

        # Queue the delivery task
        deliver_webhook.delay(str(delivery.id))

        logger.info(
            "webhook_delivery_queued",
            delivery_id=str(delivery.id),
            endpoint_id=str(endpoint.id),
            endpoint_name=endpoint.name,
            event_type=event_type,
        )

    logger.info(
        "webhook_dispatch_complete",
        event_type=event_type,
        org_id=org_id,
        delivery_count=len(delivery_ids),
    )

    return delivery_ids

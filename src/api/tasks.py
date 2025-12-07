"""
Celery tasks with idempotency, retry behavior, and DLQ routing.
"""

import hashlib
import json
from functools import wraps
from typing import Any

import structlog
from celery import shared_task
from django.conf import settings
from django.core.cache import caches

logger = structlog.get_logger(__name__)


def get_dedup_cache():
    """Get the Redis cache used for task deduplication."""
    return caches["default"]


def task_dedup_key(task_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a deduplication key for a task based on its name and arguments."""
    payload = json.dumps({"task": task_name, "args": args, "kwargs": kwargs}, sort_keys=True)
    return f"task_dedup:{hashlib.sha256(payload.encode()).hexdigest()}"


def idempotent_task(func):
    """
    Decorator to make a task idempotent using Redis-based deduplication.

    Prevents the same task from being executed multiple times within the TTL window.
    Uses task arguments to generate a unique deduplication key.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        dedup_key = task_dedup_key(self.name, args, kwargs)
        cache = get_dedup_cache()
        ttl = getattr(settings, "CELERY_TASK_DEDUP_TTL", 3600)

        # Check if this task was already processed
        if cache.get(dedup_key):
            logger.info(
                "task_deduplicated",
                task=self.name,
                task_id=self.request.id,
                dedup_key=dedup_key,
            )
            return {"status": "deduplicated", "task_id": self.request.id}

        # Mark task as being processed (set before execution to prevent races)
        cache.set(dedup_key, {"task_id": self.request.id, "status": "processing"}, ttl)

        try:
            result = func(self, *args, **kwargs)
            # Update status to completed
            cache.set(
                dedup_key,
                {"task_id": self.request.id, "status": "completed", "result": str(result)[:200]},
                ttl,
            )
            return result
        except Exception as exc:
            # Clear dedup key on failure to allow retry
            cache.delete(dedup_key)
            raise exc

    return wrapper


def route_to_dlq(task, exc, task_id, args, kwargs, einfo):
    """
    Error handler that routes failed tasks to the DLQ after max retries.
    """
    logger.error(
        "task_routed_to_dlq",
        task=task.name,
        task_id=task_id,
        exception=str(exc),
        args=args,
        kwargs=kwargs,
    )
    # The task is already failed - we just log it
    # In production, you might want to store this in a database for analysis


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    on_failure=route_to_dlq,
)
@idempotent_task
def audit_fan_out(self, event_type: str, event_data: dict, targets: list[str]) -> dict[str, Any]:
    """
    Sample idempotent task that fans out audit events to multiple targets.

    This demonstrates:
    - Idempotency via dedup decorator
    - Automatic retry with exponential backoff
    - Structured logging
    - DLQ routing on permanent failure

    Args:
        event_type: Type of audit event (e.g., "user.created", "org.updated")
        event_data: Dictionary containing event details
        targets: List of target identifiers to receive the audit event

    Returns:
        Dictionary with processing results for each target
    """
    logger.info(
        "audit_fan_out_start",
        task_id=self.request.id,
        event_type=event_type,
        target_count=len(targets),
    )

    results = {}
    for target in targets:
        try:
            # Simulate processing (in reality, this might send to an external service)
            results[target] = {"status": "delivered", "event_type": event_type}
            logger.info(
                "audit_delivered",
                task_id=self.request.id,
                target=target,
                event_type=event_type,
            )
        except Exception as e:
            logger.error(
                "audit_delivery_failed",
                task_id=self.request.id,
                target=target,
                error=str(e),
            )
            results[target] = {"status": "failed", "error": str(e)}

    logger.info(
        "audit_fan_out_complete",
        task_id=self.request.id,
        event_type=event_type,
        results_count=len(results),
    )

    return results


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    on_failure=route_to_dlq,
)
@idempotent_task
def process_webhook_event(self, webhook_type: str, payload: dict) -> dict[str, Any]:
    """
    Sample idempotent task for processing webhook events.

    Demonstrates processing external webhook events with idempotency
    to handle potential duplicate deliveries.

    Args:
        webhook_type: Type of webhook (e.g., "stripe", "github")
        payload: The webhook payload data

    Returns:
        Processing result dictionary
    """
    logger.info(
        "webhook_processing_start",
        task_id=self.request.id,
        webhook_type=webhook_type,
        payload_keys=list(payload.keys()),
    )

    # Simulate webhook processing
    result = {
        "webhook_type": webhook_type,
        "processed": True,
        "task_id": self.request.id,
    }

    logger.info(
        "webhook_processing_complete",
        task_id=self.request.id,
        webhook_type=webhook_type,
    )

    return result


@shared_task(
    bind=True,
    max_retries=0,  # No retries - immediate DLQ on failure
    acks_late=True,
    on_failure=route_to_dlq,
)
def force_fail_task(self, should_fail: bool = True) -> dict:
    """
    Test task that can be forced to fail for testing DLQ routing.

    Args:
        should_fail: If True, raises an exception to trigger failure handling

    Returns:
        Success message if not failing
    """
    logger.info("force_fail_task_start", task_id=self.request.id, should_fail=should_fail)

    if should_fail:
        raise ValueError("Intentional failure for testing DLQ routing")

    return {"status": "success", "task_id": self.request.id}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def send_email_task(
    self, to: list[str], subject: str, template: str, context: dict, from_email: str = None
):
    from api.email import send_email

    return send_email(to, subject, template, context, from_email)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def deliver_webhook(self, delivery_id: str) -> dict:
    """
    Deliver a webhook to its configured endpoint.

    This task handles the actual HTTP delivery of webhook payloads. It:
    - Fetches the delivery record from the database
    - Signs the payload using HMAC-SHA256
    - POSTs to the endpoint URL with appropriate headers
    - Updates the delivery status and stores the response

    Args:
        delivery_id: UUID of the WebhookDelivery record

    Returns:
        Dictionary with delivery status and response information
    """
    import time

    import requests
    from django.utils import timezone

    from api.models import WebhookDelivery
    from api.webhooks import sign_payload

    try:
        delivery = WebhookDelivery.objects.select_related("endpoint").get(id=delivery_id)
    except WebhookDelivery.DoesNotExist:
        logger.error("webhook_delivery_not_found", delivery_id=delivery_id)
        return {"status": "error", "message": "Delivery not found"}

    endpoint = delivery.endpoint

    if not endpoint.is_active:
        logger.warning(
            "webhook_endpoint_inactive",
            delivery_id=delivery_id,
            endpoint_id=str(endpoint.id),
        )
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.response_body = "Endpoint is inactive"
        delivery.save()
        return {"status": "skipped", "message": "Endpoint is inactive"}

    logger.info(
        "webhook_delivery_attempt",
        delivery_id=delivery_id,
        endpoint_id=str(endpoint.id),
        endpoint_url=endpoint.url,
        event_type=delivery.event_type,
        attempt=delivery.attempts + 1,
    )

    # Generate signature
    timestamp = int(time.time())
    signature = sign_payload(delivery.payload, endpoint.secret, timestamp)

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": str(timestamp),
        "X-Webhook-Event": delivery.event_type,
        "User-Agent": "Django-Webhook-Delivery/1.0",
    }

    # Add custom headers from endpoint configuration
    if endpoint.headers:
        headers.update(endpoint.headers)

    # Update delivery record
    delivery.attempts += 1
    delivery.last_attempt_at = timezone.now()

    try:
        # Make the HTTP request
        response = requests.post(
            endpoint.url,
            json=delivery.payload,
            headers=headers,
            timeout=30,  # 30 second timeout
        )

        delivery.response_status = response.status_code
        delivery.response_body = response.text[:5000]  # Limit to 5000 chars

        # Consider 2xx status codes as successful
        if 200 <= response.status_code < 300:
            delivery.status = WebhookDelivery.Status.DELIVERED
            logger.info(
                "webhook_delivered",
                delivery_id=delivery_id,
                endpoint_id=str(endpoint.id),
                status_code=response.status_code,
                attempts=delivery.attempts,
            )
        else:
            delivery.status = WebhookDelivery.Status.FAILED
            logger.warning(
                "webhook_delivery_failed_status",
                delivery_id=delivery_id,
                endpoint_id=str(endpoint.id),
                status_code=response.status_code,
                attempts=delivery.attempts,
            )

        delivery.save()

        return {
            "status": "delivered"
            if delivery.status == WebhookDelivery.Status.DELIVERED
            else "failed",
            "delivery_id": delivery_id,
            "response_status": response.status_code,
            "attempts": delivery.attempts,
        }

    except requests.exceptions.RequestException as e:
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.response_body = str(e)[:5000]
        delivery.save()

        logger.error(
            "webhook_delivery_exception",
            delivery_id=delivery_id,
            endpoint_id=str(endpoint.id),
            error=str(e),
            attempts=delivery.attempts,
        )

        # Re-raise to trigger Celery retry
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    on_failure=route_to_dlq,
)
def log_audit_task(
    self,
    action: str,
    resource_type: str,
    resource_id: str,
    changes: dict = None,
    metadata: dict = None,
    actor_id: str = None,
    actor_email: str = None,
    org_id: str = None,
) -> dict:
    """
    Asynchronously create an audit log entry via Celery.

    This task allows audit logging to be done asynchronously without
    blocking the main request/response cycle. Useful for high-volume
    operations where audit logging performance is not critical.

    Args:
        action: The action performed (create, update, delete, read, login, logout)
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        changes: Dictionary of field changes
        metadata: Additional metadata to store
        actor_id: ID of the user performing the action
        actor_email: Email of the actor
        org_id: Organization ID

    Returns:
        Dictionary with task status and audit log ID
    """
    from api.audit import log_audit

    logger.info(
        "audit_task_start",
        task_id=self.request.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    # Create the audit log entry
    audit_log = log_audit(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        metadata=metadata,
        actor_id=actor_id,
        actor_email=actor_email,
        org_id=org_id,
    )

    logger.info(
        "audit_task_complete",
        task_id=self.request.id,
        audit_id=str(audit_log.id),
        action=action,
        resource_type=resource_type,
    )

    return {
        "status": "success",
        "task_id": self.request.id,
        "audit_id": str(audit_log.id),
    }

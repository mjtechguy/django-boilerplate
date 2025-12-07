"""
Core audit logging functions for compliance and debugging.

This module provides:
- Synchronous audit logging (log_audit)
- Asynchronous audit logging via Celery (log_audit_async)
- PII handling based on AUDIT_PII_POLICY setting
- Integration with request context from config.observability
"""

import hashlib
from typing import Any, Optional

import structlog
from django.conf import settings

from config.observability import get_request_context

logger = structlog.get_logger(__name__)


def _mask_pii(value: str) -> str:
    """Mask PII by showing only first/last 2 chars."""
    if not value or len(value) <= 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def _hash_pii(value: str) -> str:
    """Hash PII using SHA256."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _handle_pii(value: Optional[str], policy: str = "mask") -> Optional[str]:
    """
    Handle PII based on the configured policy.

    Args:
        value: The PII value to handle
        policy: One of "mask", "hash", or "drop"

    Returns:
        Processed value or None if dropped
    """
    if not value:
        return value

    if policy == "mask":
        return _mask_pii(value)
    elif policy == "hash":
        return _hash_pii(value)
    elif policy == "drop":
        return None
    else:
        # Default to mask if unknown policy
        return _mask_pii(value)


def log_audit(
    action: str,
    resource_type: str,
    resource_id: str,
    changes: Optional[dict] = None,
    metadata: Optional[dict] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    org_id: Optional[str] = None,
):
    """
    Create an audit log entry synchronously.

    Args:
        action: The action performed (create, update, delete, read, login, logout)
        resource_type: Type of resource affected (e.g., "Org", "User", "SampleResource")
        resource_id: ID of the affected resource
        changes: Dictionary of field changes (for updates)
        metadata: Additional metadata to store
        actor_id: ID of the user performing the action (auto-detected from request context if not provided)
        actor_email: Email of the actor (PII handling applied)
        org_id: Organization ID (auto-detected from request context if not provided)

    Returns:
        The created AuditLog instance
    """
    from api.models import AuditLog

    # Get request context if actor/org not explicitly provided
    context = get_request_context()

    if actor_id is None:
        actor_id = context.get("actor", "system")

    if org_id is None:
        org_id = context.get("org_id", "")

    request_id = context.get("request_id", "")

    # Handle PII for actor_email
    pii_policy = getattr(settings, "AUDIT_PII_POLICY", "mask")
    if actor_email:
        actor_email = _handle_pii(actor_email, pii_policy)

    # Create the audit log entry
    audit_log = AuditLog.objects.create(
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        actor_id=str(actor_id),
        actor_email=actor_email,
        org_id=str(org_id) if org_id else None,
        changes=changes or {},
        metadata=metadata or {},
        request_id=request_id,
    )

    logger.info(
        "audit_log_created",
        audit_id=str(audit_log.id),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        actor_id=str(actor_id),
        org_id=org_id,
        request_id=request_id,
    )

    return audit_log


def log_audit_async(
    action: str,
    resource_type: str,
    resource_id: str,
    changes: Optional[dict] = None,
    metadata: Optional[dict] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Any:
    """
    Queue an audit log entry to be created asynchronously via Celery.

    This is useful for non-critical audit logging that shouldn't block
    the main request/response cycle.

    Args:
        action: The action performed
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        changes: Dictionary of field changes
        metadata: Additional metadata to store
        actor_id: ID of the user performing the action
        actor_email: Email of the actor
        org_id: Organization ID

    Returns:
        Celery AsyncResult object
    """
    from api.tasks import log_audit_task

    # Get request context to capture it before async execution
    context = get_request_context()

    if actor_id is None:
        actor_id = context.get("actor", "system")

    if org_id is None:
        org_id = context.get("org_id", "")

    # Queue the task
    return log_audit_task.delay(
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        changes=changes or {},
        metadata=metadata or {},
        actor_id=str(actor_id),
        actor_email=actor_email,
        org_id=str(org_id) if org_id else None,
    )

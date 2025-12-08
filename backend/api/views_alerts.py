"""
Admin alerts endpoint that aggregates alerts from multiple sources.

Sources:
- Audit log security events (failed logins, permission denials)
- System health issues (degraded/unhealthy components)
- Webhook delivery failures
"""

import time
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from celery import current_app
from django.conf import settings
from django.core.cache import caches
from django.db import connection
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import AuditLog, WebhookDelivery
from api.permissions import IsPlatformAdmin

logger = structlog.get_logger(__name__)


class AlertListView(APIView):
    """
    Aggregated alerts from multiple sources for admin dashboard.
    Returns recent alerts sorted by timestamp (newest first).
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get aggregated alerts from all sources."""
        limit = int(request.query_params.get("limit", 10))
        hours = int(request.query_params.get("hours", 24))

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        alerts = []

        # Collect alerts from all sources
        alerts.extend(self._get_audit_alerts(since, limit))
        alerts.extend(self._get_system_alerts())
        alerts.extend(self._get_webhook_alerts(since, limit))

        # Sort by timestamp (newest first) and limit
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        alerts = alerts[:limit]

        return Response({
            "count": len(alerts),
            "results": alerts,
        })

    def _get_audit_alerts(self, since, limit):
        """Get security-related audit log entries as alerts."""
        alerts = []

        # Query for security-relevant audit events
        security_actions = ["login_failed", "permission_denied", "mfa_failed", "account_locked"]

        audit_entries = AuditLog.objects.filter(
            timestamp__gte=since,
            action__in=security_actions,
        ).order_by("-timestamp")[:limit]

        for entry in audit_entries:
            severity = "error" if entry.action in ["account_locked", "permission_denied"] else "warning"

            message = self._format_audit_message(entry)

            alerts.append({
                "id": str(entry.id),
                "severity": severity,
                "message": message,
                "source": "audit",
                "timestamp": entry.timestamp.isoformat(),
                "metadata": {
                    "action": entry.action,
                    "actor_id": entry.actor_id,
                    "actor_email": entry.actor_email,
                    "resource_type": entry.resource_type,
                    "org_id": entry.org_id,
                },
            })

        return alerts

    def _format_audit_message(self, entry):
        """Format audit entry into human-readable message."""
        actor = entry.actor_email or entry.actor_id or "Unknown"

        messages = {
            "login_failed": f"Failed login attempt for {actor}",
            "permission_denied": f"Permission denied for {actor} on {entry.resource_type}",
            "mfa_failed": f"MFA verification failed for {actor}",
            "account_locked": f"Account locked for {actor} due to failed attempts",
        }

        return messages.get(entry.action, f"{entry.action} by {actor}")

    def _get_system_alerts(self):
        """Get alerts from system health checks."""
        alerts = []
        now = datetime.now(timezone.utc)

        # Check database
        db_status = self._check_component_health("database", self._check_database)
        if db_status:
            alerts.append({
                "id": str(uuid.uuid4()),
                "severity": db_status["severity"],
                "message": db_status["message"],
                "source": "system",
                "timestamp": now.isoformat(),
                "metadata": {"component": "database"},
            })

        # Check cache (Redis)
        cache_status = self._check_component_health("cache", self._check_cache)
        if cache_status:
            alerts.append({
                "id": str(uuid.uuid4()),
                "severity": cache_status["severity"],
                "message": cache_status["message"],
                "source": "system",
                "timestamp": now.isoformat(),
                "metadata": {"component": "cache"},
            })

        # Check Celery
        celery_status = self._check_component_health("celery", self._check_celery)
        if celery_status:
            alerts.append({
                "id": str(uuid.uuid4()),
                "severity": celery_status["severity"],
                "message": celery_status["message"],
                "source": "system",
                "timestamp": now.isoformat(),
                "metadata": {"component": "celery"},
            })

        # Check message broker
        broker_status = self._check_component_health("broker", self._check_broker)
        if broker_status:
            alerts.append({
                "id": str(uuid.uuid4()),
                "severity": broker_status["severity"],
                "message": broker_status["message"],
                "source": "system",
                "timestamp": now.isoformat(),
                "metadata": {"component": "broker"},
            })

        return alerts

    def _check_component_health(self, name, check_func):
        """Check a component and return alert info if unhealthy."""
        try:
            status = check_func()
            if status != "healthy":
                return {
                    "severity": "error" if status == "unhealthy" else "warning",
                    "message": f"{name.title()} is {status}",
                }
        except Exception as e:
            logger.warning(f"Failed to check {name} health", error=str(e))
            return {
                "severity": "error",
                "message": f"{name.title()} health check failed",
            }
        return None

    def _check_database(self):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return "healthy"
        except Exception:
            return "unhealthy"

    def _check_cache(self):
        """Check Redis cache connectivity."""
        try:
            cache = caches["default"]
            cache.set("health_check", "ok", 10)
            if cache.get("health_check") == "ok":
                return "healthy"
            return "degraded"
        except Exception:
            return "unhealthy"

    def _check_celery(self):
        """Check Celery worker availability."""
        try:
            inspect = current_app.control.inspect(timeout=2.0)
            active = inspect.active()
            if active and len(active) > 0:
                return "healthy"
            return "degraded"
        except Exception:
            return "unhealthy"

    def _check_broker(self):
        """Check message broker connectivity."""
        try:
            conn = current_app.connection()
            conn.ensure_connection(max_retries=1)
            conn.release()
            return "healthy"
        except Exception:
            return "unhealthy"

    def _get_webhook_alerts(self, since, limit):
        """Get failed webhook delivery alerts."""
        alerts = []

        failed_deliveries = WebhookDelivery.objects.filter(
            status=WebhookDelivery.Status.FAILED,
            updated_at__gte=since,
        ).select_related("endpoint").order_by("-updated_at")[:limit]

        for delivery in failed_deliveries:
            endpoint_url = delivery.endpoint.url if delivery.endpoint else "Unknown"
            # Truncate URL for display
            display_url = endpoint_url[:50] + "..." if len(endpoint_url) > 50 else endpoint_url

            alerts.append({
                "id": str(delivery.id),
                "severity": "error",
                "message": f"Webhook delivery failed to {display_url}",
                "source": "webhook",
                "timestamp": delivery.updated_at.isoformat(),
                "metadata": {
                    "endpoint_id": str(delivery.endpoint_id) if delivery.endpoint_id else None,
                    "event_type": delivery.event_type,
                    "attempts": delivery.attempts,
                    "response_code": delivery.response_code,
                },
            })

        return alerts

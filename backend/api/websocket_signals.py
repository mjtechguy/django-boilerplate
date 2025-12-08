"""
Example integration: Broadcasting WebSocket events from Django signals.

This module demonstrates how to integrate WebSocket broadcasting with Django's
signal system to automatically notify users about model changes in real-time.
"""
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from api.consumers import broadcast_notification, broadcast_org_event
from api.models import SampleResource, Membership


@receiver(post_save, sender=SampleResource)
def resource_saved_handler(sender, instance, created, **kwargs):
    """
    Broadcast organization event when a resource is created or updated.

    This handler demonstrates:
    - Async to sync conversion for signal handlers
    - Broadcasting to organization members
    - Different event types for create vs update
    """
    event_type = "resource.created" if created else "resource.updated"

    async_to_sync(broadcast_org_event)(
        org_id=str(instance.org_id),
        event_type=event_type,
        data={
            "resource_id": str(instance.id),
            "resource_name": instance.name,
            "org_id": str(instance.org_id),
            "team_id": str(instance.team_id) if instance.team else None,
            "sensitivity": instance.sensitivity,
            "timestamp": timezone.now().isoformat(),
        }
    )


@receiver(post_delete, sender=SampleResource)
def resource_deleted_handler(sender, instance, **kwargs):
    """
    Broadcast organization event when a resource is deleted.
    """
    async_to_sync(broadcast_org_event)(
        org_id=str(instance.org_id),
        event_type="resource.deleted",
        data={
            "resource_id": str(instance.id),
            "resource_name": instance.name,
            "org_id": str(instance.org_id),
            "timestamp": timezone.now().isoformat(),
        }
    )


@receiver(post_save, sender=Membership)
def membership_created_handler(sender, instance, created, **kwargs):
    """
    Notify both the user and the organization when a new membership is created.

    Demonstrates:
    - Sending both user notifications and org events
    - Notifying specific users about their actions
    """
    if not created:
        return

    # Notify the user who was added
    async_to_sync(broadcast_notification)(
        user_id=instance.user.username,
        notification={
            "title": "Added to Organization",
            "body": f"You have been added to {instance.org.name}",
            "org_id": str(instance.org_id),
            "org_name": instance.org.name,
            "timestamp": timezone.now().isoformat(),
            "action_url": f"/orgs/{instance.org_id}",
        }
    )

    # Notify all org members about the new member
    async_to_sync(broadcast_org_event)(
        org_id=str(instance.org_id),
        event_type="member.joined",
        data={
            "user_id": instance.user.username,
            "user_email": instance.user.email,
            "org_id": str(instance.org_id),
            "team_id": str(instance.team_id) if instance.team else None,
            "roles": instance.org_roles,
            "timestamp": timezone.now().isoformat(),
        }
    )


# Example: Custom notification function that can be called from views/tasks
def notify_user_task_completed(user_id: str, task_name: str, result_url: str = None):
    """
    Helper function to send task completion notifications.

    Can be called from Celery tasks or views to notify users.

    Example:
        from api.websocket_signals import notify_user_task_completed
        notify_user_task_completed(
            user_id="user-123",
            task_name="Export Data",
            result_url="/downloads/export-123.csv"
        )
    """
    notification = {
        "title": "Task Completed",
        "body": f"{task_name} has completed successfully",
        "task_name": task_name,
        "timestamp": timezone.now().isoformat(),
    }

    if result_url:
        notification["action_url"] = result_url
        notification["action_label"] = "View Result"

    async_to_sync(broadcast_notification)(user_id, notification)


def notify_org_system_alert(org_id: str, alert_type: str, message: str, severity: str = "info"):
    """
    Broadcast system alerts to organization members.

    Example:
        from api.websocket_signals import notify_org_system_alert
        notify_org_system_alert(
            org_id="org-123",
            alert_type="quota_warning",
            message="Your organization is approaching its storage quota",
            severity="warning"
        )
    """
    async_to_sync(broadcast_org_event)(
        org_id=org_id,
        event_type="system.alert",
        data={
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": timezone.now().isoformat(),
        }
    )

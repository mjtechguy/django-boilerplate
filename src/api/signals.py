"""
Django signal handlers for automatic audit logging.

This module connects to pre_save, post_save and post_delete signals to automatically
create audit log entries when models are created, updated, or deleted.
"""

from typing import Any, Dict

import structlog
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from api.audit import log_audit
from api.models import AuditLog, Membership, Org, SampleResource, Settings, Team

logger = structlog.get_logger(__name__)

# Store old values before save for change tracking
_old_values_cache: Dict[str, Dict[str, Any]] = {}


def _get_cache_key(instance: Any) -> str:
    """Generate a cache key for the instance."""
    return f"{instance.__class__.__name__}:{instance.pk}"


def _capture_old_values(instance: Any) -> None:
    """Capture old values from database before save."""
    if instance.pk:
        try:
            old_instance = instance.__class__.objects.get(pk=instance.pk)
            old_values = {}
            for field in instance._meta.fields:
                field_name = field.name
                if field_name in ["id", "created_at", "updated_at"]:
                    continue
                value = getattr(old_instance, field_name, None)
                if value is not None and not isinstance(value, (str, int, float, bool, dict, list)):
                    value = str(value)
                old_values[field_name] = value
            _old_values_cache[_get_cache_key(instance)] = old_values
        except instance.__class__.DoesNotExist:
            pass


def _get_field_changes(instance: Any, created: bool) -> Dict[str, Any]:
    """
    Get field changes by comparing current instance with cached old values.

    For created instances, returns all fields as "new" values.
    For updates, compares with the cached old values.

    Args:
        instance: The model instance
        created: Whether this is a new instance

    Returns:
        Dictionary of field changes in format: {field: {"old": ..., "new": ...}}
    """
    changes = {}

    if created:
        # For new instances, all fields are "new"
        for field in instance._meta.fields:
            field_name = field.name
            if field_name in ["id", "created_at", "updated_at"]:
                continue
            value = getattr(instance, field_name, None)
            if value is not None and not isinstance(value, (str, int, float, bool, dict, list)):
                value = str(value)
            changes[field_name] = {"old": None, "new": value}
        return changes

    # For updates, compare with cached old values
    cache_key = _get_cache_key(instance)
    old_values = _old_values_cache.pop(cache_key, {})

    for field in instance._meta.fields:
        field_name = field.name
        if field_name in ["id", "created_at", "updated_at"]:
            continue

        old_value = old_values.get(field_name)
        new_value = getattr(instance, field_name, None)

        if new_value is not None and not isinstance(new_value, (str, int, float, bool, dict, list)):
            new_value = str(new_value)

        if old_value != new_value:
            changes[field_name] = {"old": old_value, "new": new_value}

    return changes


# Pre-save signals to capture old values
@receiver(pre_save, sender=Org)
def capture_org_old_values(sender, instance, **kwargs):
    _capture_old_values(instance)


@receiver(pre_save, sender=Team)
def capture_team_old_values(sender, instance, **kwargs):
    _capture_old_values(instance)


@receiver(pre_save, sender=Membership)
def capture_membership_old_values(sender, instance, **kwargs):
    _capture_old_values(instance)


@receiver(pre_save, sender=Settings)
def capture_settings_old_values(sender, instance, **kwargs):
    _capture_old_values(instance)


@receiver(pre_save, sender=SampleResource)
def capture_sample_resource_old_values(sender, instance, **kwargs):
    _capture_old_values(instance)


@receiver(post_save, sender=Org)
def audit_org_save(sender, instance, created, **kwargs):
    """Audit Org creation and updates."""
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    changes = _get_field_changes(instance, created)

    log_audit(
        action=action,
        resource_type="Org",
        resource_id=instance.id,
        changes=changes,
        org_id=str(instance.id),
    )


@receiver(post_delete, sender=Org)
def audit_org_delete(sender, instance, **kwargs):
    """Audit Org deletion."""
    log_audit(
        action=AuditLog.Action.DELETE,
        resource_type="Org",
        resource_id=instance.id,
        metadata={"name": instance.name},
        org_id=str(instance.id),
    )


@receiver(post_save, sender=Team)
def audit_team_save(sender, instance, created, **kwargs):
    """Audit Team creation and updates."""
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    changes = _get_field_changes(instance, created)

    log_audit(
        action=action,
        resource_type="Team",
        resource_id=instance.id,
        changes=changes,
        org_id=str(instance.org_id),
    )


@receiver(post_delete, sender=Team)
def audit_team_delete(sender, instance, **kwargs):
    """Audit Team deletion."""
    log_audit(
        action=AuditLog.Action.DELETE,
        resource_type="Team",
        resource_id=instance.id,
        metadata={"name": instance.name, "org_id": str(instance.org_id)},
        org_id=str(instance.org_id),
    )


@receiver(post_save, sender=Membership)
def audit_membership_save(sender, instance, created, **kwargs):
    """Audit Membership creation and updates."""
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    changes = _get_field_changes(instance, created)

    log_audit(
        action=action,
        resource_type="Membership",
        resource_id=instance.id,
        changes=changes,
        org_id=str(instance.org_id),
    )


@receiver(post_delete, sender=Membership)
def audit_membership_delete(sender, instance, **kwargs):
    """Audit Membership deletion."""
    log_audit(
        action=AuditLog.Action.DELETE,
        resource_type="Membership",
        resource_id=instance.id,
        metadata={
            "user_id": str(instance.user_id),
            "org_id": str(instance.org_id),
            "team_id": str(instance.team_id) if instance.team_id else None,
        },
        org_id=str(instance.org_id),
    )


@receiver(post_save, sender=Settings)
def audit_settings_save(sender, instance, created, **kwargs):
    """Audit Settings creation and updates."""
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    changes = _get_field_changes(instance, created)

    log_audit(
        action=action,
        resource_type="Settings",
        resource_id=instance.id,
        changes=changes,
        org_id=str(instance.org_id) if instance.org_id else None,
    )


@receiver(post_delete, sender=Settings)
def audit_settings_delete(sender, instance, **kwargs):
    """Audit Settings deletion."""
    log_audit(
        action=AuditLog.Action.DELETE,
        resource_type="Settings",
        resource_id=instance.id,
        metadata={
            "scope": instance.scope,
            "key": instance.key,
            "org_id": str(instance.org_id) if instance.org_id else None,
        },
        org_id=str(instance.org_id) if instance.org_id else None,
    )


@receiver(post_save, sender=SampleResource)
def audit_sample_resource_save(sender, instance, created, **kwargs):
    """Audit SampleResource creation and updates."""
    action = AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
    changes = _get_field_changes(instance, created)

    log_audit(
        action=action,
        resource_type="SampleResource",
        resource_id=instance.id,
        changes=changes,
        org_id=str(instance.org_id),
    )


@receiver(post_delete, sender=SampleResource)
def audit_sample_resource_delete(sender, instance, **kwargs):
    """Audit SampleResource deletion."""
    log_audit(
        action=AuditLog.Action.DELETE,
        resource_type="SampleResource",
        resource_id=instance.id,
        metadata={"name": instance.name, "org_id": str(instance.org_id)},
        org_id=str(instance.org_id),
    )

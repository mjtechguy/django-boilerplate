"""
Impersonation helpers for platform admin user impersonation.

Provides functions to:
- Check if a user can impersonate others (platform_admin only)
- Get impersonated user details from request
- Log impersonation actions to ImpersonationLog
"""

from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model

from api.models import ImpersonationLog

User = get_user_model()


def can_impersonate(claims: Dict[str, Any]) -> bool:
    """
    Check if the user has permission to impersonate others.

    Args:
        claims: JWT token claims dictionary

    Returns:
        True if user has platform_admin role, False otherwise
    """
    realm_roles = claims.get("realm_roles", [])
    client_roles = claims.get("client_roles", [])
    all_roles = realm_roles + client_roles
    return "platform_admin" in all_roles


def get_impersonated_user(target_user_id: str) -> Optional[User]:
    """
    Get or create the user being impersonated.

    Args:
        target_user_id: The user ID to impersonate

    Returns:
        User instance or None if not found/created
    """
    try:
        user, _ = User.objects.get_or_create(
            username=target_user_id,
            defaults={"email": f"{target_user_id}@impersonated.local"},
        )
        return user
    except Exception:  # pylint: disable=broad-except
        return None


def log_impersonation(
    admin_id: str,
    admin_email: Optional[str],
    target_user_id: str,
    target_user_email: Optional[str],
    action: str,
    endpoint: str,
    method: str,
    org_id: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ImpersonationLog:
    """
    Create an impersonation log entry.

    Args:
        admin_id: ID of the admin performing impersonation
        admin_email: Email of the admin (optional)
        target_user_id: ID of the user being impersonated
        target_user_email: Email of the target user (optional)
        action: Action being performed (start, end, or specific action)
        endpoint: API endpoint being accessed
        method: HTTP method
        org_id: Organization ID (optional)
        request_id: Request ID for correlation (optional)
        metadata: Additional metadata (optional)

    Returns:
        Created ImpersonationLog instance
    """
    return ImpersonationLog.objects.create(
        admin_id=admin_id,
        admin_email=admin_email,
        target_user_id=target_user_id,
        target_user_email=target_user_email,
        action=action,
        endpoint=endpoint,
        method=method,
        org_id=org_id,
        request_id=request_id or "",
        metadata=metadata or {},
    )


def is_impersonation_enabled() -> bool:
    """
    Check if impersonation is enabled in settings.

    Returns:
        True if impersonation is enabled, False otherwise
    """
    return getattr(settings, "IMPERSONATION_ENABLED", False)

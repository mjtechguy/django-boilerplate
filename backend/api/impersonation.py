"""
Impersonation helpers for platform admin user impersonation.

Provides functions to:
- Check if a user can impersonate others (platform_admin with MFA only)
- Get impersonated user details from request
- Log impersonation actions to ImpersonationLog
"""

from typing import Any, Dict, Optional

import structlog
from django.conf import settings
from django.contrib.auth import get_user_model

from api.models import ImpersonationLog

User = get_user_model()
logger = structlog.get_logger(__name__)


def can_impersonate(claims: Dict[str, Any]) -> bool:
    """
    Check if the user has permission to impersonate others.
    Requires both platform_admin role AND verified MFA.
    """
    # Check MFA requirement first
    mfa_acr_values = getattr(
        settings,
        "MFA_ACR_VALUES",
        ["urn:keycloak:acr:mfa", "urn:keycloak:acr:2fa"],
    )
    acr = claims.get("acr", "")
    amr = claims.get("amr", [])

    mfa_verified = acr in mfa_acr_values or any(
        method in ["otp", "mfa", "totp"] for method in amr
    )

    if not mfa_verified:
        return False

    # Check platform_admin role - check realm_access structure from Keycloak
    realm_roles = claims.get("realm_access", {}).get("roles", [])
    # Also check old format for backwards compatibility
    if not realm_roles:
        realm_roles = claims.get("realm_roles", [])

    resource_access = claims.get("resource_access", {})
    client_roles = []
    for resource, access in resource_access.items():
        if isinstance(access, dict):
            client_roles.extend(access.get("roles", []))
    # Also check old format
    if not client_roles:
        client_roles = claims.get("client_roles", [])

    all_roles = realm_roles + client_roles
    return "platform_admin" in all_roles


def get_impersonated_user(target_user_id: str, org_id: Optional[str] = None) -> Optional[User]:
    """
    Get the user being impersonated.

    The target user MUST already exist in the system. Users cannot be
    created through impersonation.

    Args:
        target_user_id: The user ID (UUID or username) to impersonate
        org_id: Optional org ID to verify membership

    Returns:
        User instance or None if not found or not authorized
    """
    try:
        # Try UUID first
        try:
            from uuid import UUID

            UUID(target_user_id)
            user = User.objects.get(id=target_user_id)
        except (ValueError, User.DoesNotExist):
            # Fall back to username lookup
            user = User.objects.get(username=target_user_id)

        # Verify org membership if org_id provided
        if org_id:
            if not user.memberships.filter(org_id=org_id).exists():
                logger.warning(
                    "impersonation_org_mismatch",
                    target_user_id=target_user_id,
                    org_id=org_id,
                )
                return None

        return user
    except User.DoesNotExist:
        logger.warning(
            "impersonation_user_not_found",
            target_user_id=target_user_id,
        )
        return None
    except Exception as e:
        logger.error(
            "impersonation_lookup_error",
            target_user_id=target_user_id,
            error=str(e),
        )
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

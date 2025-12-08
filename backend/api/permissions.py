from typing import Any, Dict, Set, Tuple

from django.utils.translation import gettext_lazy as _
from rest_framework import permissions

from api.cerbos_client import check_action


def build_principal_from_claims(claims: Dict[str, Any]) -> Tuple[str, Set[str], Dict[str, Any]]:
    """Extract principal_id, roles, and attrs from token claims."""
    principal_id = claims.get("sub", "anonymous")

    # Combine realm roles and client roles from token
    roles_list = (
        claims.get("realm_roles", []) + claims.get("client_roles", []) + claims.get("roles", [])
    )
    roles = set(roles_list)

    attrs = {
        "org_id": claims.get("org_id", ""),
        "team_ids": claims.get("team_ids", []),
        "license_tier": claims.get("license_tier", "free"),
        "mfa_level": claims.get("mfa_level", 0),
        "risk_flags": claims.get("risk_flags", []),
    }

    return principal_id, roles, attrs


class CerbosPermission(permissions.BasePermission):
    """
    Generic Cerbos permission; views can set resource_kind/actions/resource_attrs on the class.
    """

    message = _("Not authorized by policy")

    def has_permission(self, request, view):
        resource_kind = getattr(view, "resource_kind", None)
        actions = getattr(view, "actions", [])
        resource_attrs = getattr(view, "resource_attrs", {}) or {}
        resource_id = getattr(view, "resource_id", "resource")

        if not resource_kind or not actions:
            return False

        claims = getattr(request, "token_claims", {})
        principal_id, roles, principal_attrs = build_principal_from_claims(claims)

        for action in actions:
            allowed = check_action(
                principal_id=principal_id,
                roles=roles,
                principal_attrs=principal_attrs,
                resource_kind=resource_kind,
                resource_id=str(resource_id),
                resource_attrs=resource_attrs,
                action=action,
            )
            if not allowed:
                return False
        return True


def _extract_roles_from_claims(claims: Dict[str, Any]) -> list:
    """Extract roles from JWT claims, handling different token formats."""
    roles = []
    # Keycloak/local structure: realm_access.roles
    roles.extend(claims.get("realm_access", {}).get("roles", []))
    # Fallback structures
    roles.extend(claims.get("realm_roles", []))
    roles.extend(claims.get("client_roles", []))
    roles.extend(claims.get("roles", []))
    return roles


class IsPlatformAdmin(permissions.BasePermission):
    """
    Permission check for platform administrator role.
    Only users with platform_admin role are allowed.
    """

    message = _("Platform administrator access required.")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        claims = getattr(request, "token_claims", {})
        roles = _extract_roles_from_claims(claims)

        return "platform_admin" in roles


class IsOrgAdmin(permissions.BasePermission):
    """
    Permission check for organization administrator role.
    User must have org_admin role for their organization.
    """

    message = _("Organization administrator access required.")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        claims = getattr(request, "token_claims", {})
        roles = _extract_roles_from_claims(claims)

        return "org_admin" in roles


class IsAuditViewer(permissions.BasePermission):
    """
    Permission check for audit log access.

    Allowed roles:
    - platform_admin: Can view all audit logs
    - org_admin: Can view their organization's logs
    - audit_viewer: Can view their organization's logs (read-only)
    """

    message = _("You do not have permission to view audit logs.")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        claims = getattr(request, "token_claims", {})
        roles = _extract_roles_from_claims(claims)

        allowed_roles = {"platform_admin", "org_admin", "audit_viewer"}
        return bool(set(roles) & allowed_roles)

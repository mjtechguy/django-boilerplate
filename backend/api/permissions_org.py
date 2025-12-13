"""
Permission classes for organization-scoped admin operations.

These permissions allow org admins to manage their own organization
without requiring platform_admin access.
"""

from typing import Any, Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import permissions


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


def _get_org_id_from_claims(claims: Dict[str, Any]) -> str | None:
    """Extract org_id from JWT claims."""
    return claims.get("org_id")


class IsOrgAdminForOrg(permissions.BasePermission):
    """
    Permission check for org-scoped admin operations.

    Requirements:
    - User must be authenticated
    - User must have 'org_admin' role
    - User's org_id in claims must match the org_id in the URL
    - Platform admins also pass this check (they can access any org)
    """

    message = _("Organization administrator access required for this organization.")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        claims = getattr(request, "token_claims", {})
        roles = _extract_roles_from_claims(claims)

        # Platform admins can access any org
        if "platform_admin" in roles:
            return True

        # Check if user is org_admin
        if "org_admin" not in roles:
            return False

        # Get org_id from URL path parameter
        org_id_from_url = view.kwargs.get("org_id")
        if not org_id_from_url:
            # If no org_id in URL, deny access
            return False

        # Get org_id from token claims
        org_id_from_claims = _get_org_id_from_claims(claims)
        if not org_id_from_claims:
            # Org admin must have org_id in claims
            return False

        # Check if the org_id matches
        return str(org_id_from_claims) == str(org_id_from_url)


class IsDivisionAdminForDivision(permissions.BasePermission):
    """
    Permission check for division-scoped admin operations.

    Requirements:
    - User must be authenticated
    - User can access if they are:
      1. platform_admin (can access any division)
      2. org_admin of the parent organization
      3. division_admin of the specific division
    """

    message = _("Division administrator access required for this division.")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        claims = getattr(request, "token_claims", {})
        roles = _extract_roles_from_claims(claims)

        # Platform admins can access any division
        if "platform_admin" in roles:
            return True

        # Get division_id from URL path parameter
        division_id = view.kwargs.get("division_id") or view.kwargs.get("pk")
        if not division_id:
            return False

        # Import models
        from api.models import Division, Membership

        # Get the division and its parent org
        try:
            division = Division.objects.select_related("org").get(pk=division_id)
        except Division.DoesNotExist:
            return False

        # Get user_id from claims
        user_id = claims.get("sub")
        if not user_id:
            return False

        # Check if user has org_admin role for the parent org
        org_membership = Membership.objects.filter(
            user_id=user_id,
            org=division.org,
            division__isnull=True  # Org-level membership
        ).first()

        if org_membership and "org_admin" in (org_membership.org_roles or []):
            return True

        # Check if user has division_admin role for this specific division
        div_membership = Membership.objects.filter(
            user_id=user_id,
            division=division
        ).first()

        if div_membership and "division_admin" in (div_membership.division_roles or []):
            return True

        return False

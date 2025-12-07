"""
Multi-Factor Authentication (MFA) Enforcement for Keycloak JWT tokens.

This module provides utilities to enforce MFA requirements based on JWT claims
provided by Keycloak when users authenticate with OTP/TOTP.

Key JWT Claims for MFA:
    - acr (Authentication Context Class Reference): Indicates the authentication level
      Example: "urn:keycloak:acr:mfa" or "urn:keycloak:acr:2fa"
    - amr (Authentication Methods References): List of authentication methods used
      Example: ["pwd", "otp"] or ["pwd", "mfa"]
    - auth_time: Unix timestamp of when the authentication occurred

MFA Flow:
    1. User authenticates with username/password in Keycloak
    2. Keycloak prompts for OTP/TOTP (if configured for the user)
    3. Upon successful MFA, Keycloak issues a JWT with MFA claims
    4. Django backend validates these claims using this module
    5. Access is granted or denied based on MFA policy

Usage:
    # As a view mixin
    class AdminAPIView(MFARequiredMixin, APIView):
        pass

    # As a decorator
    @require_mfa
    def sensitive_view(request):
        pass

    # As middleware (global enforcement)
    Add 'api.mfa.MFAMiddleware' to MIDDLEWARE in settings
"""

from functools import wraps
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.request import Request


def _get_mfa_settings() -> Dict[str, Any]:
    """
    Get MFA-related settings from Django configuration.

    Returns:
        Dictionary with MFA configuration:
        - mfa_required: Global MFA requirement
        - mfa_required_for_admin: MFA required for admin users
        - mfa_required_endpoints: List of endpoint prefixes requiring MFA
        - mfa_acr_values: Accepted ACR values indicating MFA
    """
    return {
        "mfa_required": getattr(settings, "MFA_REQUIRED", False),
        "mfa_required_for_admin": getattr(settings, "MFA_REQUIRED_FOR_ADMIN", True),
        "mfa_required_endpoints": getattr(
            settings, "MFA_REQUIRED_ENDPOINTS", ["/api/v1/admin/", "/api/v1/audit/"]
        ),
        "mfa_acr_values": getattr(
            settings,
            "MFA_ACR_VALUES",
            ["urn:keycloak:acr:mfa", "urn:keycloak:acr:2fa"],
        ),
    }


def _extract_mfa_data_from_request(request: Request) -> Dict[str, Any]:
    """
    Extract MFA-related data from the request.

    Checks both the user object (if MFA claims were added during authentication)
    and the token_claims attached to the request.

    Args:
        request: Django REST framework request object

    Returns:
        Dictionary containing:
        - mfa_verified: Boolean indicating if MFA was completed
        - mfa_level: String ACR value or None
        - auth_methods: List of authentication methods used
        - auth_time: Unix timestamp of authentication
    """
    # Check if user object has MFA attributes (set by KeycloakJWTAuthentication)
    if hasattr(request.user, "mfa_verified"):
        return {
            "mfa_verified": request.user.mfa_verified,
            "mfa_level": getattr(request.user, "mfa_level", None),
            "auth_methods": getattr(request.user, "auth_methods", []),
            "auth_time": getattr(request.user, "auth_time", None),
        }

    # Fallback to token_claims if available
    token_claims = getattr(request, "token_claims", {})
    if not token_claims:
        return {
            "mfa_verified": False,
            "mfa_level": None,
            "auth_methods": [],
            "auth_time": None,
        }

    # Extract MFA data from claims
    acr = token_claims.get("acr", "")
    amr = token_claims.get("amr", [])
    auth_time = token_claims.get("auth_time", None)

    mfa_settings = _get_mfa_settings()
    mfa_verified = acr in mfa_settings["mfa_acr_values"] or any(
        method in ["otp", "mfa", "totp"] for method in amr
    )

    return {
        "mfa_verified": mfa_verified,
        "mfa_level": acr if acr else None,
        "auth_methods": amr if isinstance(amr, list) else [],
        "auth_time": auth_time,
    }


def _is_endpoint_mfa_required(path: str) -> bool:
    """
    Check if the given endpoint path requires MFA.

    Args:
        path: Request path (e.g., "/api/v1/admin/users/")

    Returns:
        True if the endpoint requires MFA, False otherwise
    """
    mfa_settings = _get_mfa_settings()
    for endpoint_prefix in mfa_settings["mfa_required_endpoints"]:
        if path.startswith(endpoint_prefix):
            return True
    return False


def _is_user_admin(request: Request) -> bool:
    """
    Check if the user has admin-level roles.

    Checks for platform_admin realm role or org_admin client role.

    Args:
        request: Django REST framework request object

    Returns:
        True if user is an admin, False otherwise
    """
    token_claims = getattr(request, "token_claims", {})
    if not token_claims:
        return False

    # Check realm roles
    realm_roles = token_claims.get("realm_roles", [])
    if "platform_admin" in realm_roles:
        return True

    # Check client roles
    client_roles = token_claims.get("roles", [])
    if "org_admin" in client_roles:
        return True

    return False


def check_mfa_required(request: Request, raise_exception: bool = True) -> bool:
    """
    Check if MFA is required for the current request and if it's satisfied.

    This is the main function that implements the MFA enforcement logic.

    Args:
        request: Django REST framework request object
        raise_exception: If True, raise AuthenticationFailed when MFA not satisfied

    Returns:
        True if MFA requirement is satisfied, False otherwise

    Raises:
        exceptions.AuthenticationFailed: If MFA required but not satisfied
    """
    mfa_settings = _get_mfa_settings()
    mfa_data = _extract_mfa_data_from_request(request)

    # Determine if MFA is required for this request
    mfa_required = False

    # Global MFA requirement
    if mfa_settings["mfa_required"]:
        mfa_required = True

    # Admin users require MFA
    if mfa_settings["mfa_required_for_admin"] and _is_user_admin(request):
        mfa_required = True

    # Specific endpoints require MFA
    if _is_endpoint_mfa_required(request.path):
        mfa_required = True

    # If MFA is required, check if it's satisfied
    if mfa_required and not mfa_data["mfa_verified"]:
        if raise_exception:
            raise exceptions.AuthenticationFailed(
                _(
                    "Multi-factor authentication is required for this resource. "
                    "Please complete MFA setup in your account settings."
                )
            )
        return False

    return True


class MFARequiredMixin:
    """
    View mixin that enforces MFA requirement.

    Unlike check_mfa_required(), this mixin ALWAYS requires MFA,
    regardless of global settings. Use this for views that must
    unconditionally require MFA.

    Example:
        class AdminAPIView(MFARequiredMixin, APIView):
            def get(self, request):
                return Response({"message": "Admin data"})
    """

    def initial(self, request, *args, **kwargs):
        """
        Runs before the view method. Checks MFA requirement unconditionally.
        """
        super().initial(request, *args, **kwargs)
        # Always require MFA for views using this mixin (unconditional)
        mfa_data = _extract_mfa_data_from_request(request)
        if not mfa_data["mfa_verified"]:
            raise exceptions.AuthenticationFailed(
                _(
                    "Multi-factor authentication is required for this resource. "
                    "Please complete MFA setup in your account settings."
                )
            )


def require_mfa(view_func):
    """
    Decorator that enforces MFA requirement for function-based views.

    Unlike check_mfa_required(), this decorator ALWAYS requires MFA,
    regardless of global settings. Use this for views that must
    unconditionally require MFA.

    Example:
        @require_mfa
        def sensitive_view(request):
            return JsonResponse({"message": "Sensitive data"})
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Always require MFA for decorated views (unconditional)
        mfa_data = _extract_mfa_data_from_request(request)
        if not mfa_data["mfa_verified"]:
            raise exceptions.AuthenticationFailed(
                _(
                    "Multi-factor authentication is required for this resource. "
                    "Please complete MFA setup in your account settings."
                )
            )
        return view_func(request, *args, **kwargs)

    return wrapped_view


class MFAMiddleware:
    """
    Middleware for global MFA enforcement.

    This middleware checks MFA requirements for all requests.
    It respects the MFA_REQUIRED, MFA_REQUIRED_FOR_ADMIN, and
    MFA_REQUIRED_ENDPOINTS settings.

    To enable, add to MIDDLEWARE in settings:
        'api.mfa.MFAMiddleware'

    Note: Place this middleware after authentication middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip MFA check for unauthenticated requests
        # (they will be handled by authentication layer)
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        # Check MFA requirement
        try:
            check_mfa_required(request, raise_exception=True)
        except exceptions.AuthenticationFailed as exc:
            return JsonResponse(
                {
                    "error": "MFA Required",
                    "detail": str(exc),
                },
                status=403,
            )

        return self.get_response(request)


def get_mfa_status(request: Request) -> Dict[str, Any]:
    """
    Get the current MFA status for a request.

    Useful for debugging or displaying MFA status to users.

    Args:
        request: Django REST framework request object

    Returns:
        Dictionary with MFA status information:
        - mfa_verified: Boolean
        - mfa_level: String ACR value or None
        - auth_methods: List of authentication methods
        - auth_time: Unix timestamp or None
        - mfa_required: Boolean indicating if MFA is required for this request
    """
    mfa_data = _extract_mfa_data_from_request(request)
    mfa_settings = _get_mfa_settings()

    mfa_required = False
    if mfa_settings["mfa_required"]:
        mfa_required = True
    elif mfa_settings["mfa_required_for_admin"] and _is_user_admin(request):
        mfa_required = True
    elif _is_endpoint_mfa_required(request.path):
        mfa_required = True

    return {
        **mfa_data,
        "mfa_required": mfa_required,
    }

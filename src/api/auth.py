import time
from functools import lru_cache
from typing import Any, Dict, Tuple

import requests
from authlib.jose import JsonWebKey, JsonWebToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as gettext
from rest_framework import authentication, exceptions

User = get_user_model()


@lru_cache(maxsize=1)
def _jwks_cache() -> Tuple[float, Dict[str, Any]]:
    """Return (fetched_at, jwks). Cached to reduce network calls."""
    response = requests.get(settings.KEYCLOAK_JWKS_URL, timeout=5)
    response.raise_for_status()
    return time.time(), response.json()


def get_jwks() -> Dict[str, Any]:
    fetched_at, jwks = _jwks_cache()
    # Refresh JWKS every 10 minutes
    if time.time() - fetched_at > 600:
        _jwks_cache.cache_clear()
        fetched_at, jwks = _jwks_cache()
    return jwks


class KeycloakJWTAuthentication(authentication.BaseAuthentication):
    """
    DRF auth that validates Keycloak-issued JWTs and maps to a shadow Django user.
    Supports user impersonation for platform_admin users.
    """

    www_authenticate_realm = "Keycloak"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth or auth[0].lower() != b"bearer":
            return None
        if len(auth) == 1:
            raise exceptions.AuthenticationFailed(
                gettext("Invalid token header. No credentials provided.")
            )
        if len(auth) > 2:
            raise exceptions.AuthenticationFailed(
                gettext("Invalid token header. Token string should not contain spaces.")
            )

        token = auth[1].decode("utf-8")
        claims = self._validate_token(token)

        # Handle impersonation
        impersonate_header = getattr(settings, "IMPERSONATION_HEADER", "X-Impersonate-User")
        target_user_id = request.META.get(f"HTTP_{impersonate_header.upper().replace('-', '_')}")

        if target_user_id:
            # Check if impersonation is enabled
            from api.impersonation import (
                can_impersonate,
                get_impersonated_user,
                is_impersonation_enabled,
                log_impersonation,
            )

            if not is_impersonation_enabled():
                raise exceptions.AuthenticationFailed(
                    gettext("Impersonation is not enabled on this server.")
                )

            # Check if user has permission to impersonate
            if not can_impersonate(claims):
                raise exceptions.AuthenticationFailed(
                    gettext("You do not have permission to impersonate users.")
                )

            # Get the impersonated user
            impersonated_user = get_impersonated_user(target_user_id)
            if not impersonated_user:
                raise exceptions.AuthenticationFailed(
                    gettext("Unable to impersonate the specified user.")
                )

            # Log the impersonation start
            log_impersonation(
                admin_id=claims["sub"],
                admin_email=claims.get("email"),
                target_user_id=target_user_id,
                target_user_email=getattr(impersonated_user, "email", None),
                action="start",
                endpoint=request.path,
                method=request.method,
                org_id=None,  # Will be set by view if available
                request_id=getattr(request, "request_id", ""),
            )

            # Set impersonation metadata on the request
            request.impersonation = {
                "is_impersonating": True,
                "admin_id": claims["sub"],
                "admin_email": claims.get("email"),
                "target_user_id": target_user_id,
            }

            # Return impersonated user
            impersonated_user.backend = "django.contrib.auth.backends.ModelBackend"

            # Attach MFA claims from the admin's token
            # Note: The admin must have MFA enabled to impersonate
            self._attach_mfa_claims(impersonated_user, claims)

            request.auth = token
            request.token_claims = claims
            return impersonated_user, token

        # Normal authentication (no impersonation)
        user, _ = User.objects.get_or_create(
            username=claims["sub"], defaults={"email": claims.get("email", "")}
        )
        user.backend = "django.contrib.auth.backends.ModelBackend"

        # Extract and attach MFA-related claims to user object
        self._attach_mfa_claims(user, claims)

        request.auth = token
        request.token_claims = claims
        request.impersonation = {"is_impersonating": False}
        return user, token

    def _validate_token(self, token: str) -> Dict[str, Any]:
        jwk_set = JsonWebKey.import_key_set(get_jwks())
        jwt = JsonWebToken(["RS256"])

        # Allow multiple issuers for dev (localhost vs container hostname)
        allowed_issuers = [settings.KEYCLOAK_ISSUER]
        if "keycloak:" in settings.KEYCLOAK_ISSUER:
            # Also accept localhost variant for local dev
            allowed_issuers.append(settings.KEYCLOAK_ISSUER.replace("keycloak:", "localhost:"))
        elif "localhost:" in settings.KEYCLOAK_ISSUER:
            allowed_issuers.append(settings.KEYCLOAK_ISSUER.replace("localhost:", "keycloak:"))

        try:
            claims = jwt.decode(
                token,
                key=jwk_set,
                claims_options={
                    "iss": {"essential": True, "values": allowed_issuers},
                },
            )
            claims.validate()  # exp, nbf, iat

            # Check audience - azp (authorized party) if aud not present
            aud = claims.get("aud") or claims.get("azp")
            if isinstance(aud, list):
                if settings.KEYCLOAK_AUDIENCE not in aud:
                    raise ValueError("Invalid audience")
            elif aud != settings.KEYCLOAK_AUDIENCE:
                raise ValueError("Invalid audience")

        except Exception as exc:  # pylint: disable=broad-except
            raise exceptions.AuthenticationFailed(gettext("Invalid token")) from exc
        return claims

    def authenticate_header(self, request):
        return f'Bearer realm="{self.www_authenticate_realm}"'

    def _attach_mfa_claims(self, user, claims: Dict[str, Any]) -> None:
        """
        Extract MFA-related claims from JWT and attach to user object.

        This method extracts:
        - acr (Authentication Context Class Reference): Indicates MFA level
        - amr (Authentication Methods References): List of auth methods used
        - auth_time: Unix timestamp of when authentication occurred

        Args:
            user: Django user object
            claims: JWT claims dictionary
        """
        # Extract ACR (Authentication Context Class Reference)
        # Examples: "urn:keycloak:acr:mfa", "urn:keycloak:acr:2fa"
        acr = claims.get("acr", "")
        user.mfa_level = acr if acr else None

        # Extract AMR (Authentication Methods References)
        # Examples: ["pwd", "otp"], ["pwd", "mfa"], ["pwd", "totp"]
        amr = claims.get("amr", [])
        user.auth_methods = amr if isinstance(amr, list) else []

        # Extract auth_time (Unix timestamp)
        user.auth_time = claims.get("auth_time", None)

        # Determine if MFA was verified based on ACR and AMR
        # Check if ACR indicates MFA or if AMR contains OTP/MFA/TOTP
        mfa_acr_values = getattr(
            settings,
            "MFA_ACR_VALUES",
            ["urn:keycloak:acr:mfa", "urn:keycloak:acr:2fa"],
        )
        user.mfa_verified = acr in mfa_acr_values or any(
            method in ["otp", "mfa", "totp"] for method in user.auth_methods
        )

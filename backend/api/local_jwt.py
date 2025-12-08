"""
Local JWT token service for local authentication.

This module provides JWT generation and validation for locally-authenticated
users, matching the token structure used by Keycloak for seamless integration.
"""

import time
import uuid
from typing import Any

from authlib.jose import JsonWebKey, JsonWebToken, JoseError
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class LocalJWTError(Exception):
    """Base exception for local JWT operations."""

    pass


class TokenExpiredError(LocalJWTError):
    """Token has expired."""

    pass


class InvalidTokenError(LocalJWTError):
    """Token is invalid."""

    pass


# Cache for auto-generated dev keys (only used in DEBUG mode)
_dev_keys_cache: dict[str, str] = {}


def _get_or_generate_dev_keys() -> tuple[str, str]:
    """
    Get or generate development keys.

    In DEBUG mode, if no keys are configured, auto-generate them once
    and cache them for the lifetime of the process.
    """
    if "private" not in _dev_keys_cache:
        import warnings

        warnings.warn(
            "LOCAL_AUTH keys not configured! Auto-generating ephemeral keys for development. "
            "These keys will change on restart. Configure LOCAL_AUTH_PRIVATE_KEY and "
            "LOCAL_AUTH_PUBLIC_KEY in .env for persistent keys.",
            UserWarning,
        )
        private_pem, public_pem = generate_key_pair()
        _dev_keys_cache["private"] = private_pem
        _dev_keys_cache["public"] = public_pem

    return _dev_keys_cache["private"], _dev_keys_cache["public"]


def _get_signing_key() -> JsonWebKey:
    """
    Get the RSA private key for signing tokens.

    In DEBUG mode, auto-generates ephemeral keys if not configured.
    Loads the key from settings.LOCAL_AUTH_PRIVATE_KEY.
    """
    private_key_pem = getattr(settings, "LOCAL_AUTH_PRIVATE_KEY", "")

    if not private_key_pem:
        # In DEBUG mode, auto-generate keys for development convenience
        if getattr(settings, "DEBUG", False):
            private_key_pem, _ = _get_or_generate_dev_keys()
        else:
            raise LocalJWTError("LOCAL_AUTH_PRIVATE_KEY not configured")

    # Handle escaped newlines from environment variables
    private_key_pem = private_key_pem.replace("\\n", "\n")
    return JsonWebKey.import_key(private_key_pem, {"kty": "RSA"})


def _get_verification_key() -> JsonWebKey:
    """
    Get the RSA public key for verifying tokens.

    In DEBUG mode, auto-generates ephemeral keys if not configured.
    Loads the key from settings.LOCAL_AUTH_PUBLIC_KEY.
    """
    public_key_pem = getattr(settings, "LOCAL_AUTH_PUBLIC_KEY", "")

    if not public_key_pem:
        # In DEBUG mode, auto-generate keys for development convenience
        if getattr(settings, "DEBUG", False):
            _, public_key_pem = _get_or_generate_dev_keys()
        else:
            raise LocalJWTError("LOCAL_AUTH_PUBLIC_KEY not configured")

    # Handle escaped newlines from environment variables
    public_key_pem = public_key_pem.replace("\\n", "\n")
    return JsonWebKey.import_key(public_key_pem, {"kty": "RSA"})


def generate_access_token(
    user: User,
    roles: list[str] | None = None,
    org_id: str | None = None,
    ttl: int | None = None,
) -> str:
    """
    Generate a local access token for the given user.

    The token structure matches Keycloak format for compatibility
    with the existing authorization system.

    Args:
        user: The Django user to create a token for
        roles: List of roles (platform_admin, org_admin, etc.)
        org_id: Optional organization ID for org-scoped tokens
        ttl: Token time-to-live in seconds (default from settings)

    Returns:
        JWT access token string
    """
    if ttl is None:
        ttl = getattr(settings, "LOCAL_AUTH_ACCESS_TOKEN_TTL", 3600)

    issuer = getattr(settings, "LOCAL_AUTH_ISSUER", "local")
    audience = getattr(settings, "KEYCLOAK_AUDIENCE", "api")
    now = int(time.time())

    # Build claims to match Keycloak structure
    claims = {
        "iss": issuer,
        "sub": str(user.id),
        "aud": audience,
        "azp": audience,
        "exp": now + ttl,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "auth_time": now,
        # User info claims
        "email": user.email,
        "email_verified": getattr(user, "local_profile", None)
        and user.local_profile.email_verified
        or False,
        "preferred_username": user.username,
        "name": user.get_full_name() or user.username,
        "given_name": user.first_name,
        "family_name": user.last_name,
        # Role claims - match Keycloak structure
        "realm_access": {"roles": roles or []},
        "resource_access": {},
        # Mark as local token for hybrid auth
        "token_type": "local",
    }

    # Add org context if provided
    if org_id:
        claims["org_id"] = org_id

    # Sign the token with RS256
    jwt = JsonWebToken(["RS256"])
    key = _get_signing_key()
    header = {"alg": "RS256", "typ": "JWT"}

    return jwt.encode(header, claims, key).decode("utf-8")


def generate_refresh_token(
    user: User,
    ttl: int | None = None,
) -> str:
    """
    Generate a refresh token for the given user.

    Refresh tokens are longer-lived and used to obtain new access tokens.

    Args:
        user: The Django user to create a token for
        ttl: Token time-to-live in seconds (default from settings)

    Returns:
        JWT refresh token string
    """
    if ttl is None:
        ttl = getattr(settings, "LOCAL_AUTH_REFRESH_TOKEN_TTL", 604800)

    issuer = getattr(settings, "LOCAL_AUTH_ISSUER", "local")
    now = int(time.time())

    claims = {
        "iss": issuer,
        "sub": str(user.id),
        "exp": now + ttl,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "typ": "refresh",
        "token_type": "local",
    }

    jwt = JsonWebToken(["RS256"])
    key = _get_signing_key()
    header = {"alg": "RS256", "typ": "JWT"}

    return jwt.encode(header, claims, key).decode("utf-8")


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a local JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded token claims dictionary

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token is invalid
    """
    try:
        jwt = JsonWebToken(["RS256"])
        key = _get_verification_key()
        issuer = getattr(settings, "LOCAL_AUTH_ISSUER", "local")

        claims = jwt.decode(
            token,
            key=key,
            claims_options={
                "iss": {"essential": True, "value": issuer},
            },
        )
        claims.validate()
        return dict(claims)

    except JoseError as e:
        error_msg = str(e).lower()
        if "expired" in error_msg:
            raise TokenExpiredError("Token has expired") from e
        raise InvalidTokenError(f"Invalid token: {e}") from e
    except Exception as e:
        raise InvalidTokenError(f"Token verification failed: {e}") from e


def is_local_token(token: str) -> bool:
    """
    Check if a token was issued locally (not by Keycloak).

    This does a lightweight check without full validation by decoding
    the payload section of the JWT directly.

    Args:
        token: JWT token string to check

    Returns:
        True if the token appears to be locally issued
    """
    import base64
    import json

    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return False

        # Decode the payload (base64url-encoded)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding < 4:
            payload += "=" * padding
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)

        local_issuer = getattr(settings, "LOCAL_AUTH_ISSUER", "local")
        return claims.get("iss") == local_issuer

    except Exception:
        return False


def extract_roles_from_claims(claims: dict[str, Any]) -> tuple[list[str], list[str]]:
    """
    Extract realm and client roles from JWT claims.

    Matches Keycloak token structure for consistency.

    Args:
        claims: JWT claims dictionary

    Returns:
        Tuple of (realm_roles, client_roles)
    """
    realm_roles = claims.get("realm_access", {}).get("roles", [])

    # Extract client roles (format: resource_access.{client}.roles)
    client_roles = []
    resource_access = claims.get("resource_access", {})
    for resource, access in resource_access.items():
        if isinstance(access, dict) and "roles" in access:
            client_roles.extend(access.get("roles", []))

    return list(realm_roles), list(client_roles)


def generate_key_pair() -> tuple[str, str]:
    """
    Generate a new RSA key pair for local JWT signing.

    This is a utility function for initial setup.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Generate RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Serialize public key
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem

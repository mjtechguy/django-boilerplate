"""
HMAC signature-based authentication using S3-style access keys.

Authentication header format (legacy - still supported):
Authorization: AKSK AccessKeyId=<id>, Timestamp=<unix_timestamp>, Signature=<hmac>

Enhanced header format (recommended):
Authorization: AKSK AccessKeyId=<id>, Timestamp=<unix_timestamp>, Nonce=<uuid>, Signature=<hmac>

Legacy signature is computed as:
HMAC-SHA256(secret_access_key, timestamp + method + path)

Enhanced signature includes:
HMAC-SHA256(secret_access_key, timestamp + nonce + method + host + path + query + body_hash)

Security notes:
- Enhanced signature prevents request tampering and replay attacks
- Nonce tracking prevents replay within timestamp window
- Both formats supported for backward compatibility
"""

import hashlib
import hmac
import re
import time
import uuid
from urllib.parse import parse_qsl, urlencode

import structlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from api.models_access_keys import AccessKeyPair

logger = structlog.get_logger(__name__)
User = get_user_model()

# Signature timestamp must be within 5 minutes (configurable)
TIMESTAMP_TOLERANCE_SECONDS = getattr(settings, "AKSK_TIMESTAMP_TOLERANCE_SECONDS", 300)

# Nonce cache for replay protection
NONCE_CACHE_PREFIX = "aksk:nonce:"


class AccessKeyAuthentication(BaseAuthentication):
    """
    HMAC signature authentication using access key pairs.

    Validates requests signed with a secret access key.
    """

    keyword = "AKSK"

    def authenticate(self, request):
        """
        Authenticate the request using AKSK signature.

        Returns:
            tuple: (user, access_key_pair) if valid
            None: if no AKSK header present
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header.startswith(f"{self.keyword} "):
            return None

        try:
            credentials = self._parse_header(auth_header)
            access_key = self._validate_credentials(request, credentials)
            access_key.update_last_used()
            return (access_key.user, access_key)
        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            logger.error("access_key_auth_error", error=str(e))
            raise exceptions.AuthenticationFailed("Invalid access key authentication")

    def _parse_header(self, header: str) -> dict:
        """Parse the AKSK authorization header."""
        # Remove keyword prefix
        credentials_part = header[len(self.keyword) + 1 :]

        # Parse key=value pairs
        pattern = r"(\w+)=([^,]+)"
        matches = re.findall(pattern, credentials_part)

        if not matches:
            raise exceptions.AuthenticationFailed("Invalid authorization header format")

        credentials = {k.strip(): v.strip() for k, v in matches}

        # Required fields - Nonce is optional for backward compatibility
        required_fields = ["AccessKeyId", "Timestamp", "Signature"]
        for field in required_fields:
            if field not in credentials:
                raise exceptions.AuthenticationFailed(f"Missing {field} in authorization")

        return credentials

    def _validate_credentials(self, request, credentials: dict) -> AccessKeyPair:
        """Validate the credentials and signature."""
        access_key_id = credentials["AccessKeyId"]
        timestamp = credentials["Timestamp"]
        signature = credentials["Signature"]
        nonce = credentials.get("Nonce")  # Optional for backward compatibility

        # Validate timestamp
        try:
            request_time = int(timestamp)
        except ValueError:
            raise exceptions.AuthenticationFailed("Invalid timestamp format")

        current_time = int(time.time())
        if abs(current_time - request_time) > TIMESTAMP_TOLERANCE_SECONDS:
            raise exceptions.AuthenticationFailed("Request timestamp expired")

        # Find access key
        try:
            access_key = AccessKeyPair.objects.select_related("user").get(
                access_key_id=access_key_id,
                revoked=False,
            )
        except AccessKeyPair.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid access key")

        # Check for replay attack if nonce provided
        if nonce:
            if not self._verify_nonce(access_key_id, nonce):
                logger.warning(
                    "access_key_replay_detected",
                    access_key_id=access_key_id,
                    nonce=nonce,
                )
                raise exceptions.AuthenticationFailed("Request replay detected")

        # Verify the HMAC signature
        # Use enhanced signature if nonce is provided, otherwise use legacy
        if nonce:
            expected_signature = compute_signature_enhanced(
                secret=access_key.secret_access_key,
                timestamp=timestamp,
                nonce=nonce,
                method=request.method,
                host=request.get_host(),
                path=request.path,
                query_params=dict(request.GET),
                body=request.body if request.body else None,
            )
        else:
            # Legacy signature for backward compatibility
            expected_signature = compute_signature(
                secret=access_key.secret_access_key,
                timestamp=timestamp,
                method=request.method,
                path=request.path,
            )

        if not hmac.compare_digest(expected_signature, signature):
            logger.warning(
                "access_key_invalid_signature",
                access_key_id=access_key_id,
            )
            raise exceptions.AuthenticationFailed("Invalid signature")

        return access_key

    def _verify_nonce(self, access_key_id: str, nonce: str) -> bool:
        """
        Verify nonce has not been used before (replay protection).

        Returns True if nonce is valid (not seen before), False if replayed.
        """
        cache = caches["idempotency"]
        cache_key = f"{NONCE_CACHE_PREFIX}{access_key_id}:{nonce}"

        # Try to set the nonce with TTL matching timestamp tolerance
        # add() returns True only if key didn't exist
        return cache.add(cache_key, "1", timeout=TIMESTAMP_TOLERANCE_SECONDS)

    def authenticate_header(self, request):
        """Return the authenticate header for 401 responses."""
        return self.keyword


def compute_signature(secret: str, timestamp: str, method: str, path: str) -> str:
    """
    Compute HMAC-SHA256 signature for request (legacy format).

    Args:
        secret: The secret access key
        timestamp: Unix timestamp as string
        method: HTTP method (GET, POST, etc.)
        path: Request path

    Returns:
        Hex-encoded HMAC signature

    Note:
        This is the legacy signature format for backward compatibility.
        New clients should use compute_signature_enhanced() with nonce.
    """
    message = f"{timestamp}{method.upper()}{path}"
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def compute_signature_enhanced(
    secret: str,
    timestamp: str,
    nonce: str,
    method: str,
    host: str,
    path: str,
    query_params: dict | None = None,
    body: bytes | None = None,
) -> str:
    """
    Compute enhanced HMAC-SHA256 signature for request.

    This enhanced signature includes additional components to prevent
    request tampering and host confusion attacks.

    Args:
        secret: The secret access key
        timestamp: Unix timestamp as string
        nonce: Unique nonce for replay protection (UUID recommended)
        method: HTTP method (GET, POST, etc.)
        host: Request host header
        path: Request path
        query_params: Query parameters as dict (optional)
        body: Request body as bytes (optional)

    Returns:
        Hex-encoded HMAC signature

    Security features:
        - Nonce prevents replay attacks within timestamp window
        - Host inclusion prevents host header manipulation
        - Query params prevent parameter tampering
        - Body hash ensures payload integrity
    """
    # Canonicalize query parameters (sorted alphabetically)
    canonical_query = ""
    if query_params:
        sorted_params = sorted(query_params.items())
        canonical_query = urlencode(sorted_params)

    # Compute body hash (SHA256 of body or empty string)
    if body:
        body_hash = hashlib.sha256(body).hexdigest()
    else:
        body_hash = hashlib.sha256(b"").hexdigest()

    # Build canonical request string
    components = [
        timestamp,
        nonce,
        method.upper(),
        host.lower(),
        path,
        canonical_query,
        body_hash,
    ]
    message = "\n".join(components)

    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def generate_nonce() -> str:
    """Generate a unique nonce for AKSK requests."""
    return str(uuid.uuid4())


def verify_signature(
    access_key: AccessKeyPair,
    secret: str,
    timestamp: str,
    method: str,
    path: str,
    provided_signature: str,
) -> bool:
    """
    Verify the provided signature matches the expected signature.

    Args:
        access_key: The access key pair being used
        secret: The secret access key (plaintext)
        timestamp: Unix timestamp from request
        method: HTTP method
        path: Request path
        provided_signature: The signature from the Authorization header

    Returns:
        True if signature is valid
    """
    expected = compute_signature(secret, timestamp, method, path)
    return hmac.compare_digest(expected, provided_signature)

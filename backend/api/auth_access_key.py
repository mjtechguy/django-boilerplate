"""
HMAC signature-based authentication using S3-style access keys.

Authentication header format:
Authorization: AKSK AccessKeyId=<id>, Timestamp=<unix_timestamp>, Signature=<hmac>

Signature is computed as:
HMAC-SHA256(secret_access_key, timestamp + method + path)
"""

import hashlib
import hmac
import re
import time

import structlog
from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from api.models_access_keys import AccessKeyPair

logger = structlog.get_logger(__name__)
User = get_user_model()

# Signature timestamp must be within 5 minutes
TIMESTAMP_TOLERANCE_SECONDS = 300


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

        # Verify the HMAC signature
        # Secret is stored encrypted, so we can decrypt and use it
        expected_signature = compute_signature(
            secret=access_key.secret_access_key,  # Decrypted automatically
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

    def authenticate_header(self, request):
        """Return the authenticate header for 401 responses."""
        return self.keyword


def compute_signature(secret: str, timestamp: str, method: str, path: str) -> str:
    """
    Compute HMAC-SHA256 signature for request.

    Args:
        secret: The secret access key
        timestamp: Unix timestamp as string
        method: HTTP method (GET, POST, etc.)
        path: Request path

    Returns:
        Hex-encoded HMAC signature
    """
    message = f"{timestamp}{method.upper()}{path}"
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


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

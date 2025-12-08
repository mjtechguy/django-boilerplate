import hashlib
import hmac
import time
from typing import Any, Dict

import structlog
from django.conf import settings
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.licensing import get_license, set_stripe_sync_status, update_license
from api.models import Org

logger = structlog.get_logger(__name__)


def _get_org(org_id: str) -> Org:
    try:
        return Org.objects.get(id=org_id)
    except Org.DoesNotExist as exc:
        raise Http404 from exc


def _check_org_admin(claims: Dict[str, Any], org_id: str) -> bool:
    # Simple guard until full Cerbos policies wired for org admin
    roles = (claims.get("client_roles") or []) + (claims.get("realm_roles") or [])
    return claims.get("org_id") == str(org_id) and (
        "org_admin" in roles or "platform_admin" in roles
    )


class OrgLicenseView(APIView):
    """
    Org-scoped licensing endpoints (admin-only).
    """

    parser_classes = [JSONParser]

    def get(self, request, org_id):
        claims = getattr(request, "token_claims", {})
        if not _check_org_admin(claims, org_id):
            return Response({"detail": _("Forbidden")}, status=status.HTTP_403_FORBIDDEN)
        org = _get_org(org_id)
        return Response(get_license(org))

    def put(self, request, org_id):
        claims = getattr(request, "token_claims", {})
        if not _check_org_admin(claims, org_id):
            return Response({"detail": _("Forbidden")}, status=status.HTTP_403_FORBIDDEN)
        org = _get_org(org_id)
        tier = request.data.get("license_tier")
        feature_flags = request.data.get("feature_flags", {})
        if tier is None:
            return Response(
                {"detail": _("license_tier is required")}, status=status.HTTP_400_BAD_REQUEST
            )
        updated = update_license(org, tier, feature_flags)
        return Response(updated, status=status.HTTP_200_OK)


def _verify_stripe_signature(
    payload: bytes, sig_header: str, secret: str, tolerance: int = 300
) -> bool:
    """
    Verify Stripe webhook signature using HMAC-SHA256.

    Stripe signature format: t=timestamp,v1=signature[,v0=legacy_signature]

    Args:
        payload: Raw request body bytes
        sig_header: Value of Stripe-Signature header
        secret: Webhook signing secret from Stripe dashboard
        tolerance: Max age of signature in seconds (default 5 minutes)

    Returns:
        True if signature is valid, False otherwise
    """
    if not sig_header or not secret:
        return False

    try:
        # Parse signature header
        elements = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = int(elements.get("t", 0))
        signature = elements.get("v1", "")

        if not timestamp or not signature:
            return False

        # Check timestamp tolerance (prevent replay attacks)
        if abs(time.time() - timestamp) > tolerance:
            logger.warning(
                "stripe_webhook_signature_expired",
                timestamp=timestamp,
                current_time=int(time.time()),
            )
            return False

        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_sig, signature)

    except (ValueError, KeyError) as e:
        logger.error("stripe_webhook_signature_parse_error", error=str(e))
        return False


class StripeWebhookView(APIView):
    """
    Stripe webhook endpoint with signature verification.

    Validates webhook payloads using HMAC-SHA256 to ensure
    they originate from Stripe.
    """

    authentication_classes = []  # Stripe webhooks use signature-based auth
    permission_classes = []

    def post(self, request):
        # Get raw body for signature verification
        raw_body = request.body

        # Verify Stripe signature if enabled
        if settings.STRIPE_ENABLED:
            sig_header = request.headers.get("Stripe-Signature", "")
            webhook_secret = settings.STRIPE_WEBHOOK_SECRET

            if not webhook_secret:
                logger.error("stripe_webhook_secret_not_configured")
                return Response(
                    {"detail": _("Webhook not configured")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if not _verify_stripe_signature(raw_body, sig_header, webhook_secret):
                logger.warning(
                    "stripe_webhook_signature_invalid",
                    sig_header=sig_header[:50] if sig_header else None,
                )
                return Response(
                    {"detail": _("Invalid signature")},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # Process the webhook payload
        payload = request.data or {}
        org_id = payload.get("org_id")
        status_value = payload.get("status", "unknown")

        if not org_id:
            return Response({"detail": _("org_id required")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            org = Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return Response({"detail": _("org not found")}, status=status.HTTP_404_NOT_FOUND)

        set_stripe_sync_status(org, status_value)
        logger.info("stripe_webhook_processed", org_id=str(org_id), status=status_value)
        return Response({"received": True})

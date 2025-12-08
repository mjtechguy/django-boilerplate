import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

import structlog
from django.conf import settings
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.licensing import get_license, set_stripe_sync_status, update_license
from api.models import Org
from api.stripe_client import get_tier_features, map_price_to_tier

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

    Handles the following Stripe events:
    - checkout.session.completed: Subscription activated from checkout
    - customer.subscription.created: New subscription created
    - customer.subscription.updated: Subscription plan changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_failed: Payment failed
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

        # Parse payload
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            payload = request.data or {}

        event_type = payload.get("type", "")
        event_data = payload.get("data", {}).get("object", {})

        logger.info("stripe_webhook_received", event_type=event_type)

        # Route to appropriate handler
        handler = self._get_handler(event_type)
        if handler:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(
                    "stripe_webhook_handler_error",
                    event_type=event_type,
                    error=str(e),
                )
                # Still return 200 to prevent Stripe retries for processing errors
                return Response({"received": True, "error": str(e)})

        return Response({"received": True})

    def _get_handler(self, event_type: str):
        """Get the handler function for an event type."""
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_failed": self._handle_payment_failed,
        }
        return handlers.get(event_type)

    def _handle_checkout_completed(self, session: Dict[str, Any]):
        """Handle checkout.session.completed event."""
        org_id = session.get("metadata", {}).get("org_id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        if not org_id:
            logger.warning("checkout_completed_no_org_id", session_id=session.get("id"))
            return

        try:
            org = Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            logger.warning("checkout_completed_org_not_found", org_id=org_id)
            return

        # Update org with subscription info
        org.stripe_subscription_id = subscription_id
        if customer_id and not org.stripe_customer_id:
            org.stripe_customer_id = customer_id
        org.save(update_fields=["stripe_subscription_id", "stripe_customer_id", "updated_at"])

        logger.info(
            "checkout_completed",
            org_id=org_id,
            subscription_id=subscription_id,
        )

    def _handle_subscription_created(self, subscription: Dict[str, Any]):
        """Handle customer.subscription.created event."""
        self._update_org_from_subscription(subscription, "created")

    def _handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Handle customer.subscription.updated event."""
        self._update_org_from_subscription(subscription, "updated")

    def _handle_subscription_deleted(self, subscription: Dict[str, Any]):
        """Handle customer.subscription.deleted event - downgrade to free."""
        org_id = subscription.get("metadata", {}).get("org_id")
        customer_id = subscription.get("customer")

        org = self._find_org(org_id, customer_id)
        if not org:
            return

        # Downgrade to free tier
        update_license(org, "free", get_tier_features("free"))
        org.stripe_subscription_id = None
        org.save(update_fields=["stripe_subscription_id", "updated_at"])

        set_stripe_sync_status(org, "cancelled")

        logger.info(
            "subscription_deleted",
            org_id=str(org.id),
            previous_tier=org.license_tier,
        )

    def _handle_payment_failed(self, invoice: Dict[str, Any]):
        """Handle invoice.payment_failed event."""
        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")

        org = self._find_org(None, customer_id)
        if not org:
            return

        set_stripe_sync_status(org, "payment_failed")

        logger.warning(
            "payment_failed",
            org_id=str(org.id),
            customer_id=customer_id,
            subscription_id=subscription_id,
        )

    def _update_org_from_subscription(self, subscription: Dict[str, Any], action: str):
        """Update org license based on subscription."""
        org_id = subscription.get("metadata", {}).get("org_id")
        customer_id = subscription.get("customer")
        subscription_id = subscription.get("id")
        subscription_status = subscription.get("status")

        org = self._find_org(org_id, customer_id)
        if not org:
            return

        # Get price ID from subscription items
        items = subscription.get("items", {}).get("data", [])
        price_id = items[0].get("price", {}).get("id") if items else None

        if price_id and subscription_status == "active":
            # Map price to tier and update license
            tier = map_price_to_tier(price_id)
            features = get_tier_features(tier)
            update_license(org, tier, features)

            org.stripe_subscription_id = subscription_id
            org.save(update_fields=["stripe_subscription_id", "updated_at"])

            set_stripe_sync_status(org, "active")

            logger.info(
                f"subscription_{action}",
                org_id=str(org.id),
                tier=tier,
                subscription_id=subscription_id,
            )
        elif subscription_status in ("past_due", "unpaid"):
            set_stripe_sync_status(org, subscription_status)
            logger.warning(
                "subscription_payment_issue",
                org_id=str(org.id),
                status=subscription_status,
            )

    def _find_org(self, org_id: Optional[str], customer_id: Optional[str]) -> Optional[Org]:
        """Find org by ID or Stripe customer ID."""
        if org_id:
            try:
                return Org.objects.get(id=org_id)
            except Org.DoesNotExist:
                pass

        if customer_id:
            try:
                return Org.objects.get(stripe_customer_id=customer_id)
            except Org.DoesNotExist:
                pass

        logger.warning(
            "org_not_found_for_webhook",
            org_id=org_id,
            customer_id=customer_id,
        )
        return None

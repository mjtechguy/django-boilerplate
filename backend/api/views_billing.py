"""
Billing API endpoints for Stripe integration.

Provides endpoints for:
- Creating checkout sessions for subscription upgrades
- Managing billing portal access
- Viewing current subscription status
- Syncing Stripe customer on org creation
"""

import structlog
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Org
from api.permissions import IsPlatformAdmin
from api.stripe_client import (
    StripeNotConfiguredError,
    StripeOperationError,
    create_billing_portal_session,
    create_checkout_session,
    create_customer,
    get_customer_subscriptions,
    get_tier_features,
    map_price_to_tier,
)

logger = structlog.get_logger(__name__)


class BillingStatusView(APIView):
    """
    Get billing status for an organization.

    GET /api/v1/orgs/{org_id}/billing
    Returns current subscription, tier, and features.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, org_id):
        try:
            org = Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return Response(
                {"detail": _("Organization not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get subscription info if Stripe is enabled and customer exists
        subscription = None
        if settings.STRIPE_ENABLED and org.stripe_customer_id:
            subscriptions = get_customer_subscriptions(org.stripe_customer_id)
            # Get active subscription
            active_subs = [s for s in subscriptions if s.get("status") == "active"]
            if active_subs:
                sub = active_subs[0]
                subscription = {
                    "id": sub.get("id"),
                    "status": sub.get("status"),
                    "current_period_end": sub.get("current_period_end"),
                    "cancel_at_period_end": sub.get("cancel_at_period_end"),
                }

        return Response({
            "org_id": str(org.id),
            "stripe_enabled": settings.STRIPE_ENABLED,
            "stripe_customer_id": org.stripe_customer_id,
            "license_tier": org.license_tier,
            "feature_flags": org.feature_flags or get_tier_features(org.license_tier),
            "billing_email": org.billing_email,
            "subscription": subscription,
        })


class CheckoutSessionView(APIView):
    """
    Create a Stripe checkout session for subscription.

    POST /api/v1/orgs/{org_id}/billing/checkout
    Body: { "price_id": "price_xxx" }
    Returns: { "url": "https://checkout.stripe.com/..." }
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, org_id):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        price_id = request.data.get("price_id")
        if not price_id:
            return Response(
                {"detail": _("price_id is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            org = Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return Response(
                {"detail": _("Organization not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Ensure org has a Stripe customer
        if not org.stripe_customer_id:
            try:
                customer_id = create_customer(
                    org_id=str(org.id),
                    org_name=org.name,
                    email=org.billing_email,
                )
                org.stripe_customer_id = customer_id
                org.save(update_fields=["stripe_customer_id", "updated_at"])
            except StripeOperationError as e:
                logger.error("checkout_customer_creation_failed", org_id=str(org_id), error=str(e))
                return Response(
                    {"detail": _("Failed to create billing account")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        try:
            checkout_url = create_checkout_session(
                customer_id=org.stripe_customer_id,
                price_id=price_id,
                org_id=str(org.id),
            )
            return Response({"url": checkout_url})

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error("checkout_session_failed", org_id=str(org_id), error=str(e))
            return Response(
                {"detail": _("Failed to create checkout session")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BillingPortalView(APIView):
    """
    Create a Stripe billing portal session.

    POST /api/v1/orgs/{org_id}/billing/portal
    Returns: { "url": "https://billing.stripe.com/..." }
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, org_id):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            org = Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return Response(
                {"detail": _("Organization not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not org.stripe_customer_id:
            return Response(
                {"detail": _("No billing account for this organization")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            portal_url = create_billing_portal_session(
                customer_id=org.stripe_customer_id,
            )
            return Response({"url": portal_url})

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error("portal_session_failed", org_id=str(org_id), error=str(e))
            return Response(
                {"detail": _("Failed to create billing portal session")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateStripeCustomerView(APIView):
    """
    Create a Stripe customer for an organization.

    POST /api/v1/orgs/{org_id}/billing/customer
    Body: { "email": "billing@example.com" } (optional)
    Returns: { "customer_id": "cus_xxx" }
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, org_id):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            org = Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return Response(
                {"detail": _("Organization not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if org.stripe_customer_id:
            return Response(
                {"detail": _("Organization already has a billing account")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = request.data.get("email") or org.billing_email

        try:
            customer_id = create_customer(
                org_id=str(org.id),
                org_name=org.name,
                email=email,
            )
            org.stripe_customer_id = customer_id
            if email:
                org.billing_email = email
            org.save(update_fields=["stripe_customer_id", "billing_email", "updated_at"])

            return Response({
                "customer_id": customer_id,
                "org_id": str(org.id),
            }, status=status.HTTP_201_CREATED)

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error("customer_creation_failed", org_id=str(org_id), error=str(e))
            return Response(
                {"detail": _("Failed to create billing account")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AvailablePlansView(APIView):
    """
    Get available subscription plans.

    GET /api/v1/billing/plans
    Returns list of available plans with pricing info.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Return configured plans with their features
        plans = []
        for price_id, tier in settings.STRIPE_PRICE_TIER_MAP.items():
            if price_id and not price_id.startswith("price_"):
                # Skip placeholder values
                continue
            plans.append({
                "price_id": price_id,
                "tier": tier,
                "features": get_tier_features(tier),
            })

        # Add free tier
        plans.insert(0, {
            "price_id": None,
            "tier": "free",
            "features": get_tier_features("free"),
        })

        return Response({"plans": plans})


def ensure_stripe_customer(org: Org, email: str = None) -> str:
    """
    Ensure an organization has a Stripe customer ID.
    Creates one if it doesn't exist.

    Args:
        org: The organization
        email: Optional billing email

    Returns:
        The Stripe customer ID

    Raises:
        StripeOperationError: If customer creation fails
    """
    if org.stripe_customer_id:
        return org.stripe_customer_id

    if not settings.STRIPE_ENABLED:
        raise StripeNotConfiguredError("Stripe is not enabled")

    customer_id = create_customer(
        org_id=str(org.id),
        org_name=org.name,
        email=email or org.billing_email,
    )

    org.stripe_customer_id = customer_id
    if email:
        org.billing_email = email
    org.save(update_fields=["stripe_customer_id", "billing_email", "updated_at"])

    return customer_id

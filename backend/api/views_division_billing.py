"""
Division billing API endpoints for Stripe integration.

Provides endpoints for divisions with independent billing mode:
- Viewing division billing status
- Creating checkout sessions for division subscriptions
- Managing billing portal access for divisions
"""

import structlog
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.licensing import get_division_license
from api.models import Division
from api.permissions_org import IsDivisionAdminForDivision
from api.stripe_client import (
    StripeNotConfiguredError,
    StripeOperationError,
    create_billing_portal_session,
    create_checkout_session,
    create_customer,
    get_customer_subscriptions,
)

logger = structlog.get_logger(__name__)


class DivisionBillingStatusView(APIView):
    """
    Get billing status for a division with independent billing.

    GET /api/v1/orgs/{org_id}/divisions/{division_id}/billing
    Returns 400 if division uses inherited billing.
    """

    permission_classes = [IsAuthenticated, IsDivisionAdminForDivision]

    def get(self, request, org_id, division_id):
        division = get_object_or_404(Division, pk=division_id, org_id=org_id)

        if division.billing_mode != Division.BillingMode.INDEPENDENT:
            return Response(
                {"detail": _("Division uses inherited billing from organization")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get license info for this division
        license_info = get_division_license(division)

        # Get subscription info if Stripe is enabled and customer exists
        subscription = None
        if settings.STRIPE_ENABLED and division.stripe_customer_id:
            subscriptions = get_customer_subscriptions(division.stripe_customer_id)
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
            "division_id": str(division.id),
            "division_name": division.name,
            "org_id": str(division.org_id),
            "billing_mode": division.billing_mode,
            "stripe_enabled": settings.STRIPE_ENABLED,
            "stripe_customer_id": division.stripe_customer_id,
            "stripe_subscription_id": division.stripe_subscription_id,
            "license_tier": license_info["license_tier"],
            "feature_flags": license_info["features"],
            "billing_email": division.billing_email,
            "subscription": subscription,
        })


class DivisionCheckoutSessionView(APIView):
    """
    Create a Stripe checkout session for division subscription.

    POST /api/v1/orgs/{org_id}/divisions/{division_id}/billing/checkout
    Body: { "price_id": "price_xxx" }
    Returns: { "url": "https://checkout.stripe.com/..." }
    """

    permission_classes = [IsAuthenticated, IsDivisionAdminForDivision]

    def post(self, request, org_id, division_id):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        division = get_object_or_404(Division, pk=division_id, org_id=org_id)

        if division.billing_mode != Division.BillingMode.INDEPENDENT:
            return Response(
                {"detail": _("Division uses inherited billing from organization")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        price_id = request.data.get("price_id")
        if not price_id:
            return Response(
                {"detail": _("price_id is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure division has a Stripe customer
        if not division.stripe_customer_id:
            try:
                customer_id = create_customer(
                    org_id=str(division.id),
                    org_name=f"{division.org.name} - {division.name}",
                    email=division.billing_email,
                    metadata={
                        "division_id": str(division.id),
                        "parent_org_id": str(division.org_id),
                        "type": "division",
                    },
                )
                division.stripe_customer_id = customer_id
                division.save(update_fields=["stripe_customer_id", "updated_at"])
            except StripeOperationError as e:
                logger.error(
                    "division_checkout_customer_creation_failed",
                    division_id=str(division_id),
                    error=str(e),
                )
                return Response(
                    {"detail": _("Failed to create billing account")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        try:
            checkout_url = create_checkout_session(
                customer_id=division.stripe_customer_id,
                price_id=price_id,
                org_id=str(division.id),
            )
            return Response({"url": checkout_url})

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error(
                "division_checkout_session_failed",
                division_id=str(division_id),
                error=str(e),
            )
            return Response(
                {"detail": _("Failed to create checkout session")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DivisionBillingPortalView(APIView):
    """
    Create a Stripe billing portal session for the division.

    POST /api/v1/orgs/{org_id}/divisions/{division_id}/billing/portal
    Returns: { "url": "https://billing.stripe.com/..." }
    """

    permission_classes = [IsAuthenticated, IsDivisionAdminForDivision]

    def post(self, request, org_id, division_id):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        division = get_object_or_404(Division, pk=division_id, org_id=org_id)

        if division.billing_mode != Division.BillingMode.INDEPENDENT:
            return Response(
                {"detail": _("Division uses inherited billing from organization")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not division.stripe_customer_id:
            return Response(
                {"detail": _("No billing account for this division")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            portal_url = create_billing_portal_session(
                customer_id=division.stripe_customer_id,
            )
            return Response({"url": portal_url})

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error(
                "division_portal_session_failed",
                division_id=str(division_id),
                error=str(e),
            )
            return Response(
                {"detail": _("Failed to create billing portal session")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DivisionCreateStripeCustomerView(APIView):
    """
    Create a Stripe customer for a division.

    POST /api/v1/orgs/{org_id}/divisions/{division_id}/billing/customer
    Body: { "email": "billing@example.com" } (optional)
    Returns: { "customer_id": "cus_xxx" }
    """

    permission_classes = [IsAuthenticated, IsDivisionAdminForDivision]

    def post(self, request, org_id, division_id):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        division = get_object_or_404(Division, pk=division_id, org_id=org_id)

        if division.billing_mode != Division.BillingMode.INDEPENDENT:
            return Response(
                {"detail": _("Division uses inherited billing from organization")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if division.stripe_customer_id:
            return Response(
                {"detail": _("Division already has a billing account")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = request.data.get("email") or division.billing_email

        try:
            customer_id = create_customer(
                org_id=str(division.id),
                org_name=f"{division.org.name} - {division.name}",
                email=email,
                metadata={
                    "division_id": str(division.id),
                    "parent_org_id": str(division.org_id),
                    "type": "division",
                },
            )
            division.stripe_customer_id = customer_id
            if email:
                division.billing_email = email
            division.save(update_fields=["stripe_customer_id", "billing_email", "updated_at"])

            return Response(
                {
                    "customer_id": customer_id,
                    "division_id": str(division.id),
                    "org_id": str(division.org_id),
                },
                status=status.HTTP_201_CREATED,
            )

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error(
                "division_customer_creation_failed",
                division_id=str(division_id),
                error=str(e),
            )
            return Response(
                {"detail": _("Failed to create billing account")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

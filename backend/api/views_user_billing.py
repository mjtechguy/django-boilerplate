"""
User-level billing API endpoints for B2C Stripe integration.

Provides endpoints for individual user subscriptions:
- Get user billing status
- Create checkout session for user subscription
- Access billing portal
- Create Stripe customer for user
"""

import structlog
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models_local_auth import LocalUserProfile
from api.stripe_client import (
    StripeNotConfiguredError,
    StripeOperationError,
    create_billing_portal_session,
    create_checkout_session,
    create_customer,
    get_customer_subscriptions,
    get_tier_features,
)

logger = structlog.get_logger(__name__)


def _get_or_create_profile(user) -> LocalUserProfile:
    """Get or create LocalUserProfile for a user."""
    profile, _ = LocalUserProfile.objects.get_or_create(
        user=user,
        defaults={"password_hash": "", "auth_provider": "oidc"}
    )
    return profile


class UserBillingStatusView(APIView):
    """
    Get billing status for the current user.

    GET /api/v1/me/billing
    Returns current subscription, tier, and features.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = _get_or_create_profile(request.user)

        # Get subscription info if Stripe is enabled and customer exists
        subscription = None
        if settings.STRIPE_ENABLED and profile.stripe_customer_id:
            subscriptions = get_customer_subscriptions(profile.stripe_customer_id)
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
            "user_id": request.user.id,
            "email": request.user.email,
            "stripe_enabled": settings.STRIPE_ENABLED,
            "stripe_customer_id": profile.stripe_customer_id,
            "license_tier": profile.license_tier,
            "feature_flags": profile.feature_flags or get_tier_features(profile.license_tier),
            "subscription": subscription,
        })


class UserCheckoutSessionView(APIView):
    """
    Create a Stripe checkout session for user subscription.

    POST /api/v1/me/billing/checkout
    Body: { "price_id": "price_xxx" }
    Returns: { "url": "https://checkout.stripe.com/..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
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

        profile = _get_or_create_profile(request.user)

        # Ensure user has a Stripe customer
        if not profile.stripe_customer_id:
            try:
                customer_id = create_customer(
                    org_id=f"user_{request.user.id}",
                    org_name=request.user.get_full_name() or request.user.email,
                    email=request.user.email,
                    metadata={"type": "user", "user_id": str(request.user.id)},
                )
                profile.stripe_customer_id = customer_id
                profile.save(update_fields=["stripe_customer_id", "updated_at"])
            except StripeOperationError as e:
                logger.error(
                    "user_checkout_customer_creation_failed",
                    user_id=request.user.id,
                    error=str(e),
                )
                return Response(
                    {"detail": _("Failed to create billing account")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        try:
            # Use user-specific success/cancel URLs
            success_url = f"{settings.FRONTEND_URL}/settings/billing/success"
            cancel_url = f"{settings.FRONTEND_URL}/settings/billing"

            checkout_url = create_checkout_session(
                customer_id=profile.stripe_customer_id,
                price_id=price_id,
                org_id=f"user_{request.user.id}",
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return Response({"url": checkout_url})

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error(
                "user_checkout_session_failed",
                user_id=request.user.id,
                error=str(e),
            )
            return Response(
                {"detail": _("Failed to create checkout session")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserBillingPortalView(APIView):
    """
    Create a Stripe billing portal session for current user.

    POST /api/v1/me/billing/portal
    Returns: { "url": "https://billing.stripe.com/..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        profile = _get_or_create_profile(request.user)

        if not profile.stripe_customer_id:
            return Response(
                {"detail": _("No billing account found")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return_url = f"{settings.FRONTEND_URL}/settings/billing"
            portal_url = create_billing_portal_session(
                customer_id=profile.stripe_customer_id,
                return_url=return_url,
            )
            return Response({"url": portal_url})

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error(
                "user_portal_session_failed",
                user_id=request.user.id,
                error=str(e),
            )
            return Response(
                {"detail": _("Failed to create billing portal session")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateUserStripeCustomerView(APIView):
    """
    Create a Stripe customer for the current user.

    POST /api/v1/me/billing/customer
    Returns: { "customer_id": "cus_xxx" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_ENABLED:
            return Response(
                {"detail": _("Stripe billing is not enabled")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        profile = _get_or_create_profile(request.user)

        if profile.stripe_customer_id:
            return Response(
                {"detail": _("User already has a billing account")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer_id = create_customer(
                org_id=f"user_{request.user.id}",
                org_name=request.user.get_full_name() or request.user.email,
                email=request.user.email,
                metadata={"type": "user", "user_id": str(request.user.id)},
            )
            profile.stripe_customer_id = customer_id
            profile.save(update_fields=["stripe_customer_id", "updated_at"])

            return Response({
                "customer_id": customer_id,
                "user_id": request.user.id,
            }, status=status.HTTP_201_CREATED)

        except StripeNotConfiguredError:
            return Response(
                {"detail": _("Stripe is not configured")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StripeOperationError as e:
            logger.error(
                "user_customer_creation_failed",
                user_id=request.user.id,
                error=str(e),
            )
            return Response(
                {"detail": _("Failed to create billing account")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def get_effective_tier(user, org=None) -> str:
    """
    Get the effective license tier for a user.

    Priority: user_tier (if not free) > org_tier > 'free'

    Args:
        user: The Django User object
        org: Optional Org object

    Returns:
        The effective license tier string
    """
    # Check user's personal tier first
    try:
        profile = user.local_profile
        if profile.license_tier and profile.license_tier != "free":
            return profile.license_tier
    except LocalUserProfile.DoesNotExist:
        pass

    # Fall back to org tier
    if org and org.license_tier and org.license_tier != "free":
        return org.license_tier

    return "free"


def get_effective_features(user, org=None) -> dict:
    """
    Get the effective feature flags for a user.

    Merges user and org features, with user features taking precedence.

    Args:
        user: The Django User object
        org: Optional Org object

    Returns:
        Combined feature flags dict
    """
    tier = get_effective_tier(user, org)
    base_features = get_tier_features(tier)

    # Merge org features
    if org and org.feature_flags:
        base_features = {**base_features, **org.feature_flags}

    # Merge user features (highest priority)
    try:
        profile = user.local_profile
        if profile.feature_flags:
            base_features = {**base_features, **profile.feature_flags}
    except LocalUserProfile.DoesNotExist:
        pass

    return base_features


def update_user_license(user, tier: str, feature_flags: dict) -> None:
    """
    Update a user's license tier and feature flags.

    Args:
        user: The Django User object
        tier: The new license tier
        feature_flags: Feature flags dict
    """
    profile = _get_or_create_profile(user)
    profile.license_tier = tier
    profile.feature_flags = feature_flags
    profile.save(update_fields=["license_tier", "feature_flags", "updated_at"])

    logger.info(
        "user_license_updated",
        user_id=user.id,
        tier=tier,
    )

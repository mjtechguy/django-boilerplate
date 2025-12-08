"""
Stripe SDK wrapper for billing operations.

Provides a clean interface for Stripe API calls with proper error handling,
logging, and configuration management.
"""

from typing import Any, Optional

import stripe
import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)


def _get_stripe_client() -> stripe.StripeClient:
    """Get configured Stripe client instance."""
    if not settings.STRIPE_ENABLED:
        raise StripeNotConfiguredError("Stripe is not enabled")
    if not settings.STRIPE_SECRET_KEY:
        raise StripeNotConfiguredError("STRIPE_SECRET_KEY not configured")
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


class StripeNotConfiguredError(Exception):
    """Raised when Stripe is not properly configured."""

    pass


class StripeOperationError(Exception):
    """Raised when a Stripe operation fails."""

    def __init__(self, message: str, stripe_error: Optional[Exception] = None):
        self.message = message
        self.stripe_error = stripe_error
        super().__init__(message)


def create_customer(
    org_id: str,
    org_name: str,
    email: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """
    Create a Stripe customer for an organization.

    Args:
        org_id: The organization's UUID
        org_name: The organization's display name
        email: Optional billing email
        metadata: Optional additional metadata

    Returns:
        The Stripe customer ID

    Raises:
        StripeNotConfiguredError: If Stripe is not enabled
        StripeOperationError: If customer creation fails
    """
    try:
        client = _get_stripe_client()
        customer_metadata = {"org_id": str(org_id), **(metadata or {})}

        customer = client.customers.create(
            params={
                "name": org_name,
                "email": email,
                "metadata": customer_metadata,
            }
        )

        logger.info(
            "stripe_customer_created",
            org_id=org_id,
            customer_id=customer.id,
        )
        return customer.id

    except stripe.StripeError as e:
        logger.error(
            "stripe_customer_creation_failed",
            org_id=org_id,
            error=str(e),
        )
        raise StripeOperationError(f"Failed to create customer: {e}", e) from e


def get_customer(customer_id: str) -> Optional[dict]:
    """
    Retrieve a Stripe customer by ID.

    Args:
        customer_id: The Stripe customer ID

    Returns:
        Customer data dict or None if not found
    """
    try:
        client = _get_stripe_client()
        customer = client.customers.retrieve(customer_id)
        return customer.to_dict() if customer else None
    except stripe.StripeError as e:
        logger.warning(
            "stripe_customer_retrieve_failed",
            customer_id=customer_id,
            error=str(e),
        )
        return None


def update_customer(
    customer_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Update a Stripe customer.

    Args:
        customer_id: The Stripe customer ID
        name: Optional new name
        email: Optional new email
        metadata: Optional metadata updates

    Returns:
        True if update succeeded
    """
    try:
        client = _get_stripe_client()
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        if email:
            params["email"] = email
        if metadata:
            params["metadata"] = metadata

        if params:
            client.customers.update(customer_id, params=params)
            logger.info("stripe_customer_updated", customer_id=customer_id)
        return True

    except stripe.StripeError as e:
        logger.error(
            "stripe_customer_update_failed",
            customer_id=customer_id,
            error=str(e),
        )
        return False


def create_checkout_session(
    customer_id: str,
    price_id: str,
    org_id: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> str:
    """
    Create a Stripe Checkout session for subscription.

    Args:
        customer_id: The Stripe customer ID
        price_id: The Stripe price ID for the subscription
        org_id: The organization ID for metadata
        success_url: URL to redirect on success
        cancel_url: URL to redirect on cancel

    Returns:
        The checkout session URL

    Raises:
        StripeOperationError: If session creation fails
    """
    try:
        client = _get_stripe_client()

        session = client.checkout.sessions.create(
            params={
                "customer": customer_id,
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url or settings.STRIPE_SUCCESS_URL,
                "cancel_url": cancel_url or settings.STRIPE_CANCEL_URL,
                "metadata": {"org_id": str(org_id)},
                "subscription_data": {"metadata": {"org_id": str(org_id)}},
            }
        )

        logger.info(
            "stripe_checkout_session_created",
            org_id=org_id,
            session_id=session.id,
        )
        return session.url

    except stripe.StripeError as e:
        logger.error(
            "stripe_checkout_session_failed",
            org_id=org_id,
            error=str(e),
        )
        raise StripeOperationError(f"Failed to create checkout session: {e}", e) from e


def create_billing_portal_session(
    customer_id: str,
    return_url: Optional[str] = None,
) -> str:
    """
    Create a Stripe billing portal session.

    Args:
        customer_id: The Stripe customer ID
        return_url: URL to return to after portal

    Returns:
        The portal session URL

    Raises:
        StripeOperationError: If session creation fails
    """
    try:
        client = _get_stripe_client()

        session = client.billing_portal.sessions.create(
            params={
                "customer": customer_id,
                "return_url": return_url or settings.STRIPE_CANCEL_URL,
            }
        )

        logger.info(
            "stripe_portal_session_created",
            customer_id=customer_id,
        )
        return session.url

    except stripe.StripeError as e:
        logger.error(
            "stripe_portal_session_failed",
            customer_id=customer_id,
            error=str(e),
        )
        raise StripeOperationError(f"Failed to create portal session: {e}", e) from e


def get_subscription(subscription_id: str) -> Optional[dict]:
    """
    Retrieve a subscription by ID.

    Args:
        subscription_id: The Stripe subscription ID

    Returns:
        Subscription data dict or None if not found
    """
    try:
        client = _get_stripe_client()
        subscription = client.subscriptions.retrieve(subscription_id)
        return subscription.to_dict() if subscription else None
    except stripe.StripeError as e:
        logger.warning(
            "stripe_subscription_retrieve_failed",
            subscription_id=subscription_id,
            error=str(e),
        )
        return None


def get_customer_subscriptions(customer_id: str) -> list[dict]:
    """
    Get all subscriptions for a customer.

    Args:
        customer_id: The Stripe customer ID

    Returns:
        List of subscription dicts
    """
    try:
        client = _get_stripe_client()
        subscriptions = client.subscriptions.list(
            params={"customer": customer_id, "status": "all", "limit": 10}
        )
        return [sub.to_dict() for sub in subscriptions.data]
    except stripe.StripeError as e:
        logger.warning(
            "stripe_subscriptions_list_failed",
            customer_id=customer_id,
            error=str(e),
        )
        return []


def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> bool:
    """
    Cancel a subscription.

    Args:
        subscription_id: The Stripe subscription ID
        at_period_end: If True, cancel at end of billing period

    Returns:
        True if cancellation succeeded
    """
    try:
        client = _get_stripe_client()

        if at_period_end:
            client.subscriptions.update(
                subscription_id,
                params={"cancel_at_period_end": True},
            )
        else:
            client.subscriptions.cancel(subscription_id)

        logger.info(
            "stripe_subscription_cancelled",
            subscription_id=subscription_id,
            at_period_end=at_period_end,
        )
        return True

    except stripe.StripeError as e:
        logger.error(
            "stripe_subscription_cancel_failed",
            subscription_id=subscription_id,
            error=str(e),
        )
        return False


def map_price_to_tier(price_id: str) -> str:
    """
    Map a Stripe price ID to a license tier.

    Args:
        price_id: The Stripe price ID

    Returns:
        The license tier name, defaults to 'free' if not mapped
    """
    return settings.STRIPE_PRICE_TIER_MAP.get(price_id, "free")


def get_tier_features(tier: str) -> dict:
    """
    Get the feature flags for a license tier.

    Args:
        tier: The license tier name

    Returns:
        Feature flags dict for the tier
    """
    return settings.STRIPE_TIER_FEATURES.get(tier, settings.STRIPE_TIER_FEATURES["free"])

"""
Tests for Stripe billing integration.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Org
from api.stripe_client import (
    StripeNotConfiguredError,
    get_tier_features,
    map_price_to_tier,
)


class TierMappingTests(TestCase):
    """Test tier mapping functions."""

    @override_settings(
        STRIPE_PRICE_TIER_MAP={
            "price_starter_123": "starter",
            "price_pro_456": "pro",
        }
    )
    def test_map_price_to_tier_known_price(self):
        """Test mapping a known price ID to tier."""
        self.assertEqual(map_price_to_tier("price_starter_123"), "starter")
        self.assertEqual(map_price_to_tier("price_pro_456"), "pro")

    @override_settings(STRIPE_PRICE_TIER_MAP={})
    def test_map_price_to_tier_unknown_price(self):
        """Test mapping an unknown price ID defaults to free."""
        self.assertEqual(map_price_to_tier("price_unknown"), "free")

    @override_settings(
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5},
            "pro": {"max_users": 100},
        }
    )
    def test_get_tier_features_known_tier(self):
        """Test getting features for a known tier."""
        features = get_tier_features("pro")
        self.assertEqual(features["max_users"], 100)

    @override_settings(
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5},
        }
    )
    def test_get_tier_features_unknown_tier(self):
        """Test getting features for unknown tier defaults to free."""
        features = get_tier_features("enterprise")
        self.assertEqual(features["max_users"], 5)


class StripeClientTests(TestCase):
    """Test Stripe client wrapper."""

    @override_settings(STRIPE_ENABLED=False)
    def test_client_disabled_raises_error(self):
        """Test that operations fail when Stripe is disabled."""
        from api.stripe_client import _get_stripe_client

        with self.assertRaises(StripeNotConfiguredError):
            _get_stripe_client()

    @override_settings(STRIPE_ENABLED=True, STRIPE_SECRET_KEY="")
    def test_client_no_key_raises_error(self):
        """Test that operations fail without API key."""
        from api.stripe_client import _get_stripe_client

        with self.assertRaises(StripeNotConfiguredError):
            _get_stripe_client()


class BillingStatusViewTests(APITestCase):
    """Test billing status endpoint."""

    def setUp(self):
        self.org = Org.objects.create(
            name="Test Org",
            license_tier="free",
        )

    def _mock_validate(self, token, **kwargs):
        return {
            "sub": "test-user-123",
            "email": "test@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["platform_admin"]},
        }

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=False)
    def test_billing_status_stripe_disabled(self, mock_validate):
        """Test billing status when Stripe is disabled."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.get(f"/api/v1/orgs/{self.org.id}/billing")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["stripe_enabled"])
        self.assertEqual(response.data["license_tier"], "free")

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=True)
    def test_billing_status_no_customer(self, mock_validate):
        """Test billing status for org without Stripe customer."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.get(f"/api/v1/orgs/{self.org.id}/billing")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["stripe_enabled"])
        self.assertIsNone(response.data["stripe_customer_id"])
        self.assertIsNone(response.data["subscription"])


class CheckoutSessionViewTests(APITestCase):
    """Test checkout session endpoint."""

    def setUp(self):
        self.org = Org.objects.create(
            name="Test Org",
            license_tier="free",
            stripe_customer_id="cus_test123",
        )

    def _mock_validate(self, token, **kwargs):
        return {
            "sub": "test-user-123",
            "email": "admin@example.com",
            "preferred_username": "admin",
            "realm_access": {"roles": ["platform_admin"]},
        }

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=False)
    def test_checkout_stripe_disabled(self, mock_validate):
        """Test checkout fails when Stripe is disabled."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.post(
            f"/api/v1/orgs/{self.org.id}/billing/checkout",
            {"price_id": "price_test"},
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=True)
    def test_checkout_missing_price_id(self, mock_validate):
        """Test checkout fails without price_id."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.post(f"/api/v1/orgs/{self.org.id}/billing/checkout", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.views_billing.create_checkout_session")
    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=True, STRIPE_SECRET_KEY="sk_test_xxx")
    def test_checkout_success(self, mock_validate, mock_create_session):
        """Test successful checkout session creation."""
        mock_validate.side_effect = self._mock_validate
        mock_create_session.return_value = "https://checkout.stripe.com/session123"
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.post(
            f"/api/v1/orgs/{self.org.id}/billing/checkout",
            {"price_id": "price_test"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], "https://checkout.stripe.com/session123")


class StripeWebhookTests(APITestCase):
    """Test Stripe webhook handling."""

    def setUp(self):
        self.org = Org.objects.create(
            name="Test Org",
            license_tier="free",
            stripe_customer_id="cus_test123",
        )

    @override_settings(STRIPE_ENABLED=False)
    def test_webhook_stripe_disabled(self):
        """Test webhook processes when Stripe is disabled (no signature check)."""
        payload = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "metadata": {"org_id": str(self.org.id)},
                    "items": {"data": [{"price": {"id": "price_pro"}}]},
                }
            },
        }

        response = self.client.post(
            "/api/v1/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(STRIPE_ENABLED=True, STRIPE_WEBHOOK_SECRET="")
    def test_webhook_no_secret_configured(self):
        """Test webhook fails when secret not configured."""
        response = self.client.post(
            "/api/v1/stripe/webhook",
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @override_settings(
        STRIPE_ENABLED=False,
        STRIPE_PRICE_TIER_MAP={"price_pro": "pro"},
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5},
            "pro": {"max_users": 100},
        },
    )
    def test_webhook_subscription_created_updates_tier(self):
        """Test subscription.created webhook updates org license tier."""
        payload = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "metadata": {"org_id": str(self.org.id)},
                    "items": {"data": [{"price": {"id": "price_pro"}}]},
                }
            },
        }

        response = self.client.post(
            "/api/v1/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh org from DB
        self.org.refresh_from_db()
        self.assertEqual(self.org.license_tier, "pro")
        self.assertEqual(self.org.stripe_subscription_id, "sub_test123")

    @override_settings(
        STRIPE_ENABLED=False,
        STRIPE_TIER_FEATURES={"free": {"max_users": 5}},
    )
    def test_webhook_subscription_deleted_downgrades(self):
        """Test subscription.deleted webhook downgrades to free tier."""
        # Set org to pro first
        self.org.license_tier = "pro"
        self.org.stripe_subscription_id = "sub_test123"
        self.org.save()

        payload = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "metadata": {"org_id": str(self.org.id)},
                }
            },
        }

        response = self.client.post(
            "/api/v1/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh org from DB
        self.org.refresh_from_db()
        self.assertEqual(self.org.license_tier, "free")
        self.assertIsNone(self.org.stripe_subscription_id)

    @override_settings(STRIPE_ENABLED=False)
    def test_webhook_checkout_completed(self):
        """Test checkout.session.completed webhook updates org."""
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test123",
                    "customer": "cus_new123",
                    "subscription": "sub_new123",
                    "metadata": {"org_id": str(self.org.id)},
                }
            },
        }

        response = self.client.post(
            "/api/v1/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh org from DB
        self.org.refresh_from_db()
        self.assertEqual(self.org.stripe_subscription_id, "sub_new123")

    @override_settings(STRIPE_ENABLED=False)
    def test_webhook_payment_failed(self):
        """Test invoice.payment_failed webhook."""
        payload = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_test123",
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                }
            },
        }

        response = self.client.post(
            "/api/v1/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AvailablePlansViewTests(APITestCase):
    """Test available plans endpoint."""

    def _mock_validate(self, token, **kwargs):
        return {
            "sub": "test-user-123",
            "email": "test@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["user"]},
        }

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=False)
    def test_plans_stripe_disabled(self, mock_validate):
        """Test plans endpoint when Stripe is disabled."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.get("/api/v1/billing/plans")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(
        STRIPE_ENABLED=True,
        STRIPE_PRICE_TIER_MAP={
            "price_starter": "starter",
            "price_pro": "pro",
        },
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5},
            "starter": {"max_users": 25},
            "pro": {"max_users": 100},
        },
    )
    def test_plans_returns_all_tiers(self, mock_validate):
        """Test plans endpoint returns configured plans."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.get("/api/v1/billing/plans")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plans = response.data["plans"]
        # Should have free + configured plans
        self.assertGreaterEqual(len(plans), 1)
        # First plan should be free
        self.assertEqual(plans[0]["tier"], "free")

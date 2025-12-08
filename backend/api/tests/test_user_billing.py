"""
Tests for B2C user-level Stripe billing integration.
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from api.models_local_auth import LocalUserProfile
from api.views_user_billing import get_effective_tier, get_effective_features

User = get_user_model()


class UserBillingModelTests(TestCase):
    """Test user billing model fields."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_profile_has_stripe_fields(self):
        """Test LocalUserProfile has Stripe billing fields."""
        profile = LocalUserProfile.objects.create(
            user=self.user,
            password_hash="hash",
        )
        self.assertIsNone(profile.stripe_customer_id)
        self.assertIsNone(profile.stripe_subscription_id)
        self.assertEqual(profile.license_tier, "free")
        self.assertEqual(profile.feature_flags, {})

    def test_profile_stripe_customer_id_indexed(self):
        """Test stripe_customer_id is indexed."""
        profile = LocalUserProfile.objects.create(
            user=self.user,
            password_hash="hash",
            stripe_customer_id="cus_test123",
        )
        # Query by customer ID should work
        found = LocalUserProfile.objects.get(stripe_customer_id="cus_test123")
        self.assertEqual(found.id, profile.id)


class EffectiveTierTests(TestCase):
    """Test effective tier calculation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.profile = LocalUserProfile.objects.create(
            user=self.user,
            password_hash="hash",
        )

    def test_default_tier_is_free(self):
        """Test default tier is free when no subscription."""
        tier = get_effective_tier(self.user)
        self.assertEqual(tier, "free")

    def test_user_tier_takes_precedence(self):
        """Test user tier takes precedence over org tier."""
        from api.models import Org

        org = Org.objects.create(name="Test Org", license_tier="starter")
        self.profile.license_tier = "pro"
        self.profile.save()

        tier = get_effective_tier(self.user, org)
        self.assertEqual(tier, "pro")

    def test_org_tier_used_when_user_is_free(self):
        """Test org tier is used when user has no subscription."""
        from api.models import Org

        org = Org.objects.create(name="Test Org", license_tier="pro")
        self.profile.license_tier = "free"
        self.profile.save()

        tier = get_effective_tier(self.user, org)
        self.assertEqual(tier, "pro")


class EffectiveFeaturesTests(TestCase):
    """Test effective feature flags calculation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.profile = LocalUserProfile.objects.create(
            user=self.user,
            password_hash="hash",
        )

    @override_settings(
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5, "webhooks_enabled": False},
            "pro": {"max_users": 100, "webhooks_enabled": True},
        }
    )
    def test_features_from_tier(self):
        """Test features come from effective tier."""
        self.profile.license_tier = "pro"
        self.profile.save()

        features = get_effective_features(self.user)
        self.assertEqual(features["max_users"], 100)
        self.assertTrue(features["webhooks_enabled"])

    @override_settings(
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5},
        }
    )
    def test_user_features_override(self):
        """Test user-specific features take precedence."""
        self.profile.feature_flags = {"custom_feature": True, "max_users": 10}
        self.profile.save()

        features = get_effective_features(self.user)
        self.assertTrue(features["custom_feature"])
        self.assertEqual(features["max_users"], 10)


class UserBillingStatusViewTests(APITestCase):
    """Test user billing status endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def _mock_validate(self, token, **kwargs):
        return {
            "sub": str(self.user.id),
            "email": self.user.email,
            "preferred_username": self.user.username,
            "realm_access": {"roles": ["user"]},
        }

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=False)
    def test_billing_status_stripe_disabled(self, mock_validate):
        """Test billing status when Stripe is disabled."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.get("/api/v1/me/billing")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["stripe_enabled"])
        self.assertEqual(response.data["license_tier"], "free")

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=True)
    def test_billing_status_no_customer(self, mock_validate):
        """Test billing status for user without Stripe customer."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.get("/api/v1/me/billing")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["stripe_enabled"])
        self.assertIsNone(response.data["stripe_customer_id"])
        self.assertIsNone(response.data["subscription"])


class UserCheckoutSessionViewTests(APITestCase):
    """Test user checkout session endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.profile = LocalUserProfile.objects.create(
            user=self.user,
            password_hash="hash",
            stripe_customer_id="cus_test123",
        )

    def _mock_validate(self, token, **kwargs):
        return {
            "sub": str(self.user.id),
            "email": self.user.email,
            "preferred_username": self.user.username,
            "realm_access": {"roles": ["user"]},
        }

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=False)
    def test_checkout_stripe_disabled(self, mock_validate):
        """Test checkout fails when Stripe is disabled."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.post(
            "/api/v1/me/billing/checkout",
            {"price_id": "price_test"},
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=True)
    def test_checkout_missing_price_id(self, mock_validate):
        """Test checkout fails without price_id."""
        mock_validate.side_effect = self._mock_validate
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.post("/api/v1/me/billing/checkout", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.views_user_billing.create_checkout_session")
    @patch("api.views_user_billing.create_customer")
    @patch("api.auth.KeycloakJWTAuthentication._validate_token")
    @override_settings(STRIPE_ENABLED=True, STRIPE_SECRET_KEY="sk_test_xxx")
    def test_checkout_success(self, mock_validate, mock_create_customer, mock_create_session):
        """Test successful checkout session creation."""
        mock_validate.side_effect = self._mock_validate
        mock_create_customer.return_value = "cus_new_user123"
        mock_create_session.return_value = "https://checkout.stripe.com/session123"
        self.client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")

        response = self.client.post(
            "/api/v1/me/billing/checkout",
            {"price_id": "price_test"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], "https://checkout.stripe.com/session123")


class UserWebhookTests(APITestCase):
    """Test Stripe webhook handling for user subscriptions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.profile = LocalUserProfile.objects.create(
            user=self.user,
            password_hash="hash",
            stripe_customer_id="cus_test123",
        )

    @override_settings(
        STRIPE_ENABLED=False,
        STRIPE_PRICE_TIER_MAP={"price_pro": "pro"},
        STRIPE_TIER_FEATURES={
            "free": {"max_users": 5},
            "pro": {"max_users": 100},
        },
    )
    def test_webhook_user_subscription_created(self):
        """Test subscription.created webhook for user updates tier."""
        payload = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "metadata": {
                        "type": "user",
                        "org_id": f"user_{self.user.id}",
                    },
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

        # Refresh profile from DB
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.license_tier, "pro")
        self.assertEqual(self.profile.stripe_subscription_id, "sub_test123")

    @override_settings(
        STRIPE_ENABLED=False,
        STRIPE_TIER_FEATURES={"free": {"max_users": 5}},
    )
    def test_webhook_user_subscription_deleted(self):
        """Test subscription.deleted webhook for user downgrades to free."""
        # Set user to pro first
        self.profile.license_tier = "pro"
        self.profile.stripe_subscription_id = "sub_test123"
        self.profile.save()

        payload = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "metadata": {
                        "type": "user",
                        "org_id": f"user_{self.user.id}",
                    },
                }
            },
        }

        response = self.client.post(
            "/api/v1/stripe/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh profile from DB
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.license_tier, "free")
        self.assertIsNone(self.profile.stripe_subscription_id)

    @override_settings(STRIPE_ENABLED=False)
    def test_webhook_routes_by_org_id_prefix(self):
        """Test webhook routes to user handler based on org_id prefix."""
        payload = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "metadata": {
                        "org_id": f"user_{self.user.id}",  # No explicit type, uses prefix
                    },
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

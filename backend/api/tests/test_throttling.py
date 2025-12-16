"""
Tests for per-tenant (organization) rate limiting.
"""

import uuid

import pytest
from django.core.cache import caches
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import Org
from api.throttling import OrgRateThrottle
from api.views import AuthPingView

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def clear_throttle_cache():
    """Clear the throttle cache before each test."""
    cache = caches["idempotency"]
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def enable_throttling():
    """Enable OrgRateThrottle on AuthPingView for tests.

    DRF caches settings at import time, so override_settings doesn't work.
    Instead, we directly patch the throttle_classes on the view.
    """
    original_classes = AuthPingView.throttle_classes
    AuthPingView.throttle_classes = [OrgRateThrottle]
    yield
    AuthPingView.throttle_classes = original_classes


@pytest.fixture
def mock_auth(monkeypatch):
    """
    Patch KeycloakJWTAuthentication._validate_token to bypass JWKS calls.
    """

    def _mock_validate(self, token):
        # Extract org_id from token if it follows pattern "token-{org_id}"
        org_id = None
        if token.startswith("token-"):
            org_id = token.split("-", 1)[1]

        return {
            "sub": "user-123",
            "email": "user@example.com",
            "realm_roles": ["user"],
            "client_roles": [],
            "org_id": org_id,
        }

    monkeypatch.setattr("api.auth.KeycloakJWTAuthentication._validate_token", _mock_validate)
    return _mock_validate


@pytest.fixture
def free_org():
    """Create a free tier organization."""
    return Org.objects.create(
        id=uuid.uuid4(),
        name="Free Org",
        license_tier="free",
        status=Org.Status.ACTIVE,
    )


@pytest.fixture
def starter_org():
    """Create a starter tier organization."""
    return Org.objects.create(
        id=uuid.uuid4(),
        name="Starter Org",
        license_tier="starter",
        status=Org.Status.ACTIVE,
    )


@pytest.fixture
def pro_org():
    """Create a pro tier organization."""
    return Org.objects.create(
        id=uuid.uuid4(),
        name="Pro Org",
        license_tier="pro",
        status=Org.Status.ACTIVE,
    )


@pytest.fixture
def enterprise_org():
    """Create an enterprise tier organization."""
    return Org.objects.create(
        id=uuid.uuid4(),
        name="Enterprise Org",
        license_tier="enterprise",
        status=Org.Status.ACTIVE,
    )


@pytest.fixture
def custom_rate_org():
    """Create an organization with custom rate limit in feature_flags."""
    return Org.objects.create(
        id=uuid.uuid4(),
        name="Custom Rate Org",
        license_tier="free",
        status=Org.Status.ACTIVE,
        feature_flags={"api_rate_limit": 50},
    )


def test_free_tier_rate_limit(client, mock_auth, free_org, clear_throttle_cache, enable_throttling):
    """Test that free tier has 100 requests/hour limit."""
    token = f"token-{free_org.id}"

    # Free tier should allow 100 requests/hour
    # Make 100 requests - all should succeed
    for i in range(100):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200, f"Request {i+1} failed with status {resp.status_code}"

    # 101st request should be throttled
    resp = client.get(
        reverse("api-ping"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp.status_code == 429, "Expected throttling after 100 requests"


def test_starter_tier_rate_limit(client, mock_auth, starter_org, clear_throttle_cache, enable_throttling):
    """Test that starter tier has 1000 requests/hour limit."""
    token = f"token-{starter_org.id}"

    # Starter tier should allow 1000 requests/hour
    # We'll just test a subset to keep test fast
    for i in range(50):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200, f"Request {i+1} failed"


def test_pro_tier_rate_limit(client, mock_auth, pro_org, clear_throttle_cache, enable_throttling):
    """Test that pro tier has 10000 requests/hour limit."""
    token = f"token-{pro_org.id}"

    # Pro tier should allow 10000 requests/hour
    # We'll just test a subset to keep test fast
    for i in range(100):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200, f"Request {i+1} failed"


def test_enterprise_tier_unlimited(client, mock_auth, enterprise_org, clear_throttle_cache, enable_throttling):
    """Test that enterprise tier has unlimited requests."""
    token = f"token-{enterprise_org.id}"

    # Enterprise tier should have no limit
    # Test a large number of requests
    for i in range(200):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200, f"Request {i+1} failed"


def test_custom_rate_limit_in_feature_flags(
    client, mock_auth, custom_rate_org, clear_throttle_cache, enable_throttling
):
    """Test that custom rate limit in feature_flags overrides tier default."""
    token = f"token-{custom_rate_org.id}"

    # Custom rate is 50/hour
    for i in range(50):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200, f"Request {i+1} failed"

    # 51st request should be throttled
    resp = client.get(
        reverse("api-ping"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp.status_code == 429, "Expected throttling after 50 requests"


def test_different_orgs_have_independent_limits(
    client, mock_auth, free_org, starter_org, clear_throttle_cache, enable_throttling
):
    """Test that different organizations have independent rate limits."""
    free_token = f"token-{free_org.id}"
    starter_token = f"token-{starter_org.id}"

    # Make 50 requests from free org
    for i in range(50):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {free_token}",
        )
        assert resp.status_code == 200

    # Make 50 requests from starter org - should not be affected by free org's count
    for i in range(50):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {starter_token}",
        )
        assert resp.status_code == 200

    # Free org should still have 50 more requests available
    for i in range(50):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {free_token}",
        )
        assert resp.status_code == 200

    # 101st request from free org should be throttled
    resp = client.get(
        reverse("api-ping"),
        HTTP_AUTHORIZATION=f"Bearer {free_token}",
    )
    assert resp.status_code == 429


def test_no_org_id_skips_org_throttling(client, mock_auth, clear_throttle_cache, enable_throttling):
    """Test that requests without org_id skip org-level throttling."""
    # Use a token that doesn't contain org_id
    token = "token-without-org"

    # Should fall back to user/anon throttling which has higher limits
    # Make 50 requests - should all succeed
    for i in range(50):
        resp = client.get(
            reverse("api-ping"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert resp.status_code == 200

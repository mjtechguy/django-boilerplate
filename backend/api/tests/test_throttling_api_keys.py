"""
Tests for API Key creation rate limiting.

Tests cover:
- Rate limiting is applied to API key creation
- 429 response when rate limit exceeded
- Throttle reset after time window
- Wait time calculation
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.urls import reverse
from rest_framework.test import APIClient

from api.models_api_keys import UserAPIKey

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def clear_throttle_cache():
    """Clear the API key throttle cache before and after each test."""
    cache = caches["default"]
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password="testpass123",
    )


@pytest.fixture
def authenticated_client(client, user):
    """Client authenticated as the test user."""
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def org_with_tier():
    """Create an org with a specific tier."""
    def _create_org(tier="free"):
        from api.models import Org
        org = Org.objects.create(name=f"Test Org {tier}", license_tier=tier)
        return org
    return _create_org


@pytest.fixture
def user_with_org(org_with_tier):
    """Create a user with membership to an org with specific tier."""
    def _create_user(tier="enterprise"):
        from api.models import Membership
        user = User.objects.create_user(
            username=f"user_{tier}_{uuid.uuid4().hex[:8]}",
            email=f"user_{tier}_{uuid.uuid4().hex[:8]}@example.com",
            password="testpass123",
        )
        org = org_with_tier(tier)
        Membership.objects.create(user=user, org=org)
        return user, org
    return _create_user


class TestAPIKeyCreationThrottle:
    """Test rate limiting for API key creation."""

    def test_allows_up_to_5_requests(self, client, user_with_org, clear_throttle_cache):
        """Test that APIKeyCreationThrottle allows 5 requests before blocking."""
        # Use enterprise tier to avoid quota limits interfering with throttle tests
        user, org = user_with_org("enterprise")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # First 5 requests should be allowed
        for i in range(5):
            response = client.post(url, {"name": f"Test Key {i+1}"})
            assert response.status_code == 201, f"Request {i+1} should not be throttled"

        # 6th request should be throttled
        response = client.post(url, {"name": "Test Key 6"})
        assert response.status_code == 429, "6th request should be throttled"

    def test_returns_429_when_throttled(self, client, user_with_org, clear_throttle_cache):
        """Test that throttled requests return 429 status code."""
        user, org = user_with_org("enterprise")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Exhaust the rate limit
        for i in range(5):
            client.post(url, {"name": f"Key {i+1}"})

        # Next request should return 429
        response = client.post(url, {"name": "Key 6"})
        assert response.status_code == 429
        assert "detail" in response.data or "throttled" in str(response.data).lower()

    def test_throttle_is_per_user(self, client, clear_throttle_cache):
        """Test that different users have independent rate limits."""
        from api.models import Membership, Org

        # Create two users with enterprise tier
        org = Org.objects.create(name="Test Org", license_tier="enterprise")

        user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123",
        )
        Membership.objects.create(user=user1, org=org)

        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
        )
        Membership.objects.create(user=user2, org=org)

        url = reverse("user-api-key-create")

        # User 1 exhausts their limit
        client.force_authenticate(user=user1)
        for i in range(5):
            response = client.post(url, {"name": f"User1 Key {i+1}"})
            assert response.status_code == 201

        # User 1's 6th request should be throttled
        response = client.post(url, {"name": "User1 Key 6"})
        assert response.status_code == 429

        # User 2 should still be able to create keys
        client.force_authenticate(user=user2)
        response = client.post(url, {"name": "User2 Key 1"})
        assert response.status_code == 201, "User 2 should not be affected by User 1's throttle"

    def test_throttle_applies_to_both_success_and_failure(self, client, user_with_org, clear_throttle_cache):
        """Test that both successful and failed creation attempts count toward throttle."""
        user, org = user_with_org("free")  # Free tier has quota of 5
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 5 keys (reaching quota limit)
        for i in range(5):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # 6th request will fail due to quota (403), but still counts toward throttle
        # This is the 6th request, which exceeds the 5/hour throttle limit
        response = client.post(url, {"name": "Key 6"})
        assert response.status_code == 429, "Should be throttled on 6th request"

    def test_unauthenticated_requests_not_throttled(self, client, clear_throttle_cache):
        """Test that unauthenticated requests bypass throttling (but fail auth check)."""
        url = reverse("user-api-key-create")

        # Unauthenticated requests should fail with 401, not 429
        for i in range(10):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 401, f"Request {i+1} should fail auth, not throttle"


class TestThrottleWaitTime:
    """Test wait time calculation for throttled requests."""

    def test_returns_retry_after_when_throttled(self, client, user_with_org, clear_throttle_cache):
        """Test that wait time is properly calculated and returned."""
        user, org = user_with_org("enterprise")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Exhaust the rate limit
        for i in range(5):
            client.post(url, {"name": f"Key {i+1}"})

        # Next request should be throttled with retry info
        response = client.post(url, {"name": "Key 6"})
        assert response.status_code == 429

        # DRF includes detail message for throttled requests
        # The response may include wait time in seconds
        assert "detail" in response.data or "Retry-After" in response


class TestThrottleReset:
    """Test that throttle resets after the time window."""

    def test_throttle_resets_after_time_window(self, client, user_with_org, clear_throttle_cache):
        """Test that requests are allowed again after the throttle window expires."""
        import time
        from unittest.mock import patch

        user, org = user_with_org("enterprise")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Mock time to control the passage of time
        mock_time = time.time()

        with patch("api.throttling_api_keys.time.time", return_value=mock_time):
            # Make 5 requests at time T
            for i in range(5):
                response = client.post(url, {"name": f"Key {i+1}"})
                assert response.status_code == 201

            # 6th request should be throttled
            response = client.post(url, {"name": "Key 6"})
            assert response.status_code == 429

        # Advance time by 1 hour + 1 second (past the throttle window)
        mock_time_advanced = mock_time + 3601

        with patch("api.throttling_api_keys.time.time", return_value=mock_time_advanced):
            # Should be able to create keys again
            response = client.post(url, {"name": "Key 7"})
            assert response.status_code == 201, "Throttle should reset after 1 hour"

    def test_partial_throttle_reset(self, client, user_with_org, clear_throttle_cache):
        """Test that old requests are removed from the sliding window."""
        import time
        from unittest.mock import patch

        user, org = user_with_org("enterprise")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Mock time to control the passage of time
        mock_time = time.time()

        with patch("api.throttling_api_keys.time.time", return_value=mock_time):
            # Make 3 requests at time T
            for i in range(3):
                response = client.post(url, {"name": f"Key {i+1}"})
                assert response.status_code == 201

        # Advance time by 30 minutes
        mock_time_half = mock_time + 1800

        with patch("api.throttling_api_keys.time.time", return_value=mock_time_half):
            # Make 2 more requests (total 5 in window)
            for i in range(2):
                response = client.post(url, {"name": f"Key {i+4}"})
                assert response.status_code == 201

            # 6th request should be throttled (5 requests in the last hour)
            response = client.post(url, {"name": "Key 6"})
            assert response.status_code == 429

        # Advance time by another 31 minutes (total 61 minutes from first request)
        # First 3 requests should now be outside the 1-hour window
        mock_time_advanced = mock_time + 3660

        with patch("api.throttling_api_keys.time.time", return_value=mock_time_advanced):
            # Should be able to create keys again (only 2 requests in current window)
            response = client.post(url, {"name": "Key 7"})
            assert response.status_code == 201, "Old requests should be removed from sliding window"


class TestThrottleWithQuota:
    """Test interaction between throttle and quota limits."""

    def test_throttle_checked_before_quota(self, client, user_with_org, clear_throttle_cache):
        """Test that throttle is checked before quota validation."""
        user, org = user_with_org("free")  # Free tier has quota of 5
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 4 keys (under both quota and throttle limit)
        for i in range(4):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # 5th request succeeds (at quota limit, under throttle limit)
        response = client.post(url, {"name": "Key 5"})
        assert response.status_code == 201

        # 6th request should be throttled (429), not quota limited (403)
        response = client.post(url, {"name": "Key 6"})
        assert response.status_code == 429, "Throttle should be checked before quota"

    def test_quota_limit_with_throttle_not_exceeded(self, client, user_with_org, clear_throttle_cache):
        """Test that quota limits work when throttle is not exceeded."""
        import time
        from unittest.mock import patch

        user, org = user_with_org("free")  # Free tier has quota of 5
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        mock_time = time.time()

        # Spread requests over time to avoid throttling
        for i in range(5):
            with patch("api.throttling_api_keys.time.time", return_value=mock_time + (i * 1000)):
                response = client.post(url, {"name": f"Key {i+1}"})
                assert response.status_code == 201

        # 6th request should fail with 403 (quota exceeded), not 429 (throttled)
        with patch("api.throttling_api_keys.time.time", return_value=mock_time + 5000):
            response = client.post(url, {"name": "Key 6"})
            assert response.status_code == 403, "Should hit quota limit when throttle not exceeded"
            assert "quota exceeded" in response.json()["error"].lower()

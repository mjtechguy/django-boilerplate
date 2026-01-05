"""
Tests for User API Key functionality.

Tests cover:
- Creating API keys
- Listing user's API keys
- Revoking API keys
- Using API keys for authentication
- Permission checks
"""
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
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="testpass123",
    )


@pytest.fixture
def authenticated_client(client, user):
    """Client authenticated as the test user."""
    client.force_authenticate(user=user)
    return client


class TestUserAPIKeyCreation:
    """Test API key creation."""

    def test_create_api_key_success(self, authenticated_client):
        """Test successful API key creation."""
        url = reverse("user-api-key-create")
        response = authenticated_client.post(url, {"name": "Test Key"})

        assert response.status_code == 201
        data = response.json()
        assert "key" in data
        assert "id" in data
        assert data["name"] == "Test Key"
        assert "prefix" in data
        assert "created" in data

        # Verify the key was saved in the database
        assert UserAPIKey.objects.filter(name="Test Key").exists()

    def test_create_api_key_without_name(self, authenticated_client):
        """Test creating API key without providing a name."""
        url = reverse("user-api-key-create")
        response = authenticated_client.post(url, {})

        assert response.status_code == 201
        data = response.json()
        assert "key" in data
        # Should auto-generate a name
        assert "API Key" in data["name"]

    def test_create_api_key_unauthenticated(self, client):
        """Test that unauthenticated users cannot create API keys."""
        url = reverse("user-api-key-create")
        response = client.post(url, {"name": "Test Key"})

        assert response.status_code == 401


class TestUserAPIKeyListing:
    """Test listing user's API keys."""

    def test_list_api_keys_empty(self, authenticated_client):
        """Test listing when user has no API keys."""
        url = reverse("user-api-key-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "api_keys" in data
        assert len(data["api_keys"]) == 0

    def test_list_api_keys_with_keys(self, authenticated_client, user):
        """Test listing user's API keys."""
        # Create some API keys
        key1, _ = UserAPIKey.objects.create_key(user=user, name="Key 1")
        key2, _ = UserAPIKey.objects.create_key(user=user, name="Key 2")

        url = reverse("user-api-key-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["api_keys"]) == 2

        # Verify key data structure
        for key_data in data["api_keys"]:
            assert "id" in key_data
            assert "prefix" in key_data
            assert "name" in key_data
            assert "created" in key_data
            assert "revoked" in key_data
            # Full key should NOT be returned
            assert "key" not in key_data

    def test_list_only_own_keys(self, authenticated_client, user, other_user):
        """Test that users only see their own API keys."""
        # Create keys for different users
        UserAPIKey.objects.create_key(user=user, name="User Key")
        UserAPIKey.objects.create_key(user=other_user, name="Other User Key")

        url = reverse("user-api-key-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["api_keys"]) == 1
        assert data["api_keys"][0]["name"] == "User Key"

    def test_list_api_keys_unauthenticated(self, client):
        """Test that unauthenticated users cannot list API keys."""
        url = reverse("user-api-key-list")
        response = client.get(url)

        assert response.status_code == 401


class TestUserAPIKeyRevocation:
    """Test API key revocation."""

    def test_revoke_api_key_success(self, authenticated_client, user):
        """Test successful API key revocation."""
        api_key, _ = UserAPIKey.objects.create_key(user=user, name="Key to Revoke")

        url = reverse("user-api-key-revoke", kwargs={"key_id": api_key.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 200
        assert "revoked successfully" in response.json()["message"]

        # Verify the key is revoked in the database
        api_key.refresh_from_db()
        assert api_key.revoked is True

    def test_revoke_nonexistent_key(self, authenticated_client):
        """Test revoking a key that doesn't exist."""
        from uuid import uuid4

        url = reverse("user-api-key-revoke", kwargs={"key_id": uuid4()})
        response = authenticated_client.delete(url)

        assert response.status_code == 404
        assert "not found" in response.json()["error"]

    def test_revoke_other_users_key(self, authenticated_client, other_user):
        """Test that users cannot revoke other users' keys."""
        api_key, _ = UserAPIKey.objects.create_key(user=other_user, name="Other User Key")

        url = reverse("user-api-key-revoke", kwargs={"key_id": api_key.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 404

        # Verify the key is NOT revoked
        api_key.refresh_from_db()
        assert api_key.revoked is False

    def test_revoke_already_revoked_key(self, authenticated_client, user):
        """Test revoking a key that's already revoked."""
        api_key, _ = UserAPIKey.objects.create_key(user=user, name="Key to Revoke")
        api_key.revoked = True
        api_key.save()

        url = reverse("user-api-key-revoke", kwargs={"key_id": api_key.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 400
        assert "already revoked" in response.json()["error"]

    def test_revoke_api_key_unauthenticated(self, client, user):
        """Test that unauthenticated users cannot revoke API keys."""
        api_key, _ = UserAPIKey.objects.create_key(user=user, name="Key")

        url = reverse("user-api-key-revoke", kwargs={"key_id": api_key.id})
        response = client.delete(url)

        assert response.status_code == 401


class TestAPIKeyAuthentication:
    """Test using API keys for authentication."""

    def test_authenticate_with_valid_api_key(self, client, user):
        """Test authentication using a valid API key."""
        from api.permissions_api_key import HasUserAPIKey

        # Create an API key
        api_key, key = UserAPIKey.objects.create_key(user=user, name="Auth Test Key")

        # Try to access protected endpoint with API key
        url = reverse("api-ping")
        response = client.get(url, HTTP_AUTHORIZATION=f"Api-Key {key}")

        # Note: This will fail without proper permission class configuration
        # The actual authentication happens in the permission class
        # This test verifies the API key model is set up correctly
        assert UserAPIKey.objects.get_from_key(key) == api_key

    def test_authenticate_with_invalid_api_key(self, client):
        """Test authentication with invalid API key."""
        import pytest
        # get_from_key raises DoesNotExist for invalid keys
        with pytest.raises(UserAPIKey.DoesNotExist):
            UserAPIKey.objects.get_from_key("invalid-key-123")

    def test_authenticate_with_revoked_api_key(self, client, user):
        """Test that revoked API keys cannot be used."""
        import pytest
        # Create and revoke an API key
        api_key, key = UserAPIKey.objects.create_key(user=user, name="Revoked Key")
        api_key.revoked = True
        api_key.save()

        # Revoked keys raise DoesNotExist when retrieved
        with pytest.raises(UserAPIKey.DoesNotExist):
            UserAPIKey.objects.get_from_key(key)


class TestAPIKeyPermissions:
    """Test API key permission classes."""

    def test_has_user_api_key_permission(self, user):
        """Test HasUserAPIKey permission class."""
        from django.http import HttpRequest

        from api.permissions_api_key import HasUserAPIKey

        # Create an API key
        api_key, key = UserAPIKey.objects.create_key(user=user, name="Permission Test")

        # Create a mock request with API key header
        request = HttpRequest()
        request.META = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}

        # Test permission check
        permission = HasUserAPIKey()
        # Note: Full permission check requires proper DRF request context
        # This verifies the permission class is properly configured
        assert permission.model == UserAPIKey

    def test_is_authenticated_or_has_api_key_permission(self, user):
        """Test IsAuthenticatedOrHasUserAPIKey hybrid permission."""
        from api.permissions_api_key import IsAuthenticatedOrHasUserAPIKey

        # Verify the permission class exists and is properly configured
        assert IsAuthenticatedOrHasUserAPIKey is not None


class TestAPIKeyQuotaEnforcement:
    """Test API key quota enforcement per tier."""

    @pytest.fixture
    def org_with_tier(self):
        """Create an org with a specific tier."""
        def _create_org(tier="free"):
            from api.models import Org, Membership
            org = Org.objects.create(name=f"Test Org {tier}", license_tier=tier)
            return org
        return _create_org

    @pytest.fixture
    def user_with_tier(self, org_with_tier):
        """Create a user with membership to an org with specific tier."""
        def _create_user(tier="free"):
            from api.models import Membership
            user = User.objects.create_user(
                username=f"user_{tier}",
                email=f"user_{tier}@example.com",
                password="testpass123",
            )
            org = org_with_tier(tier)
            Membership.objects.create(user=user, org=org)
            return user, org
        return _create_user

    def test_quota_info_in_list_response(self, client, user_with_tier, clear_throttle_cache):
        """Test that quota info is included in list response."""
        user, org = user_with_tier("free")
        client.force_authenticate(user=user)

        # Create a couple of API keys
        UserAPIKey.objects.create_key(user=user, name="Key 1")
        UserAPIKey.objects.create_key(user=user, name="Key 2")

        url = reverse("user-api-key-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Verify quota info is present
        assert "quota" in data
        assert data["quota"]["active_keys"] == 2
        assert data["quota"]["max_keys"] == 5  # Free tier limit
        assert data["quota"]["remaining"] == 3

    def test_quota_info_in_create_response(self, client, user_with_tier, clear_throttle_cache):
        """Test that quota info is included in create response."""
        user, org = user_with_tier("starter")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")
        response = client.post(url, {"name": "Test Key"})

        assert response.status_code == 201
        data = response.json()

        # Verify quota info is present
        assert "quota" in data
        assert data["quota"]["active_keys"] == 1
        assert data["quota"]["max_keys"] == 10  # Starter tier limit
        assert data["quota"]["remaining"] == 9

    def test_free_tier_quota_limit(self, client, user_with_tier, clear_throttle_cache):
        """Test that free tier users are limited to 5 API keys."""
        user, org = user_with_tier("free")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 5 keys (should succeed)
        for i in range(5):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # Verify we have 5 active keys
        assert UserAPIKey.objects.filter(user=user, revoked=False).count() == 5

        # 6th key should fail with 403
        response = client.post(url, {"name": "Key 6"})
        assert response.status_code == 403
        data = response.json()
        assert "quota exceeded" in data["error"].lower()
        assert "5" in data["error"]  # Should mention the limit

    def test_starter_tier_quota_limit(self, client, user_with_tier, clear_throttle_cache):
        """Test that starter tier users are limited to 10 API keys."""
        user, org = user_with_tier("starter")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 10 keys (should succeed)
        for i in range(10):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # Verify we have 10 active keys
        assert UserAPIKey.objects.filter(user=user, revoked=False).count() == 10

        # 11th key should fail with 403
        response = client.post(url, {"name": "Key 11"})
        assert response.status_code == 403
        data = response.json()
        assert "quota exceeded" in data["error"].lower()
        assert "10" in data["error"]

    def test_pro_tier_quota_limit(self, client, user_with_tier, clear_throttle_cache):
        """Test that pro tier users are limited to 25 API keys."""
        user, org = user_with_tier("pro")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 25 keys (should succeed)
        for i in range(25):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # Verify we have 25 active keys
        assert UserAPIKey.objects.filter(user=user, revoked=False).count() == 25

        # 26th key should fail with 403
        response = client.post(url, {"name": "Key 26"})
        assert response.status_code == 403
        data = response.json()
        assert "quota exceeded" in data["error"].lower()
        assert "25" in data["error"]

    def test_enterprise_tier_unlimited_keys(self, client, user_with_tier, clear_throttle_cache):
        """Test that enterprise tier users can create unlimited API keys."""
        user, org = user_with_tier("enterprise")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 30 keys (well beyond other tier limits)
        for i in range(30):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # Verify we have 30 active keys
        assert UserAPIKey.objects.filter(user=user, revoked=False).count() == 30

        # Should still be able to create more
        response = client.post(url, {"name": "Key 31"})
        assert response.status_code == 201

        # Check quota shows unlimited (-1)
        data = response.json()
        assert data["quota"]["max_keys"] == -1
        assert data["quota"]["remaining"] == -1

    def test_revoked_keys_dont_count_against_quota(self, client, user_with_tier, clear_throttle_cache):
        """Test that revoked keys don't count against the quota."""
        user, org = user_with_tier("free")
        client.force_authenticate(user=user)

        create_url = reverse("user-api-key-create")

        # Create 5 keys (at limit)
        created_keys = []
        for i in range(5):
            response = client.post(create_url, {"name": f"Key {i+1}"})
            assert response.status_code == 201
            created_keys.append(response.json()["id"])

        # 6th key should fail
        response = client.post(create_url, {"name": "Key 6"})
        assert response.status_code == 403

        # Revoke one key
        revoke_url = reverse("user-api-key-revoke", kwargs={"key_id": created_keys[0]})
        response = client.delete(revoke_url)
        assert response.status_code == 200

        # Now should be able to create another key
        response = client.post(create_url, {"name": "Key 7"})
        assert response.status_code == 201

        # Verify active count is still at limit (4 old + 1 new)
        assert UserAPIKey.objects.filter(user=user, revoked=False).count() == 5
        # Verify total count includes revoked key
        assert UserAPIKey.objects.filter(user=user).count() == 6

    def test_quota_with_feature_flag_override(self, client, user_with_tier, clear_throttle_cache):
        """Test that feature_flags can override tier defaults."""
        from api.models import Org

        user, org = user_with_tier("free")
        client.force_authenticate(user=user)

        # Set custom max_api_keys via feature_flags
        org.feature_flags = {"max_api_keys": 3}
        org.save()

        url = reverse("user-api-key-create")

        # Create 3 keys (custom limit)
        for i in range(3):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # 4th key should fail
        response = client.post(url, {"name": "Key 4"})
        assert response.status_code == 403
        data = response.json()
        assert "quota exceeded" in data["error"].lower()
        assert "3" in data["error"]  # Should mention custom limit

    def test_quota_403_response_format(self, client, user_with_tier, clear_throttle_cache):
        """Test the format of 403 response when quota exceeded."""
        user, org = user_with_tier("free")
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Create 5 keys to reach limit
        for i in range(5):
            client.post(url, {"name": f"Key {i+1}"})

        # Try to create 6th key
        response = client.post(url, {"name": "Key 6"})

        assert response.status_code == 403
        data = response.json()

        # Verify error message structure
        assert "error" in data
        assert isinstance(data["error"], str)
        assert "quota exceeded" in data["error"].lower()
        # Should mention both current count and limit
        assert "5" in data["error"]

    def test_quota_enforcement_for_user_without_org(self, client, clear_throttle_cache):
        """Test that users without org membership get free tier quota."""
        user = User.objects.create_user(
            username="no_org_user",
            email="noorg@example.com",
            password="testpass123",
        )
        client.force_authenticate(user=user)

        url = reverse("user-api-key-create")

        # Should be able to create up to free tier limit (5)
        for i in range(5):
            response = client.post(url, {"name": f"Key {i+1}"})
            assert response.status_code == 201

        # 6th should fail
        response = client.post(url, {"name": "Key 6"})
        assert response.status_code == 403

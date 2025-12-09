"""
Tests for Social OAuth authentication.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from api.models_social_auth import SocialAccount

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """Create a test user."""
    from api.models_local_auth import LocalUserProfile

    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
    )
    profile = LocalUserProfile.objects.create(
        user=user,
        auth_provider="local",
        email_verified=True,
        roles=["user"],
    )
    profile.set_password("TestPass123!")
    profile.save()
    return user


@pytest.fixture
def client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(client, user, monkeypatch):
    """Create an authenticated API client."""

    def mock_validate(self, token):
        return {
            "sub": user.username,
            "email": user.email,
            "preferred_username": user.username,
            "realm_access": {"roles": ["user"]},
        }

    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token", mock_validate
    )
    client.credentials(HTTP_AUTHORIZATION="Bearer mock-token")
    return client


class TestSocialProviders:
    """Test social provider listing."""

    def test_list_providers_no_config(self, client, settings):
        """Test providers list when none configured."""
        settings.GOOGLE_CLIENT_ID = None
        settings.GITHUB_CLIENT_ID = None

        url = reverse("auth-social-providers")
        response = client.get(url)

        assert response.status_code == 200
        assert response.json()["providers"] == []

    def test_list_providers_with_google(self, client, settings):
        """Test providers list with Google configured."""
        settings.GOOGLE_CLIENT_ID = "test-client-id"
        settings.GITHUB_CLIENT_ID = None

        url = reverse("auth-social-providers")
        response = client.get(url)

        assert response.status_code == 200
        providers = response.json()["providers"]
        assert len(providers) == 1
        assert providers[0]["id"] == "google"


class TestSocialLogin:
    """Test social login URL generation."""

    def test_get_login_url_unconfigured_provider(self, client, settings):
        """Test error when provider not configured."""
        settings.GOOGLE_CLIENT_ID = None
        settings.GITHUB_CLIENT_ID = None

        url = reverse("auth-social-login", kwargs={"provider": "google"})
        response = client.get(url)

        assert response.status_code == 400
        assert "not configured" in response.json()["error"]

    def test_get_login_url_google(self, client, settings):
        """Test getting Google OAuth URL."""
        settings.GOOGLE_CLIENT_ID = "test-client-id"

        url = reverse("auth-social-login", kwargs={"provider": "google"})
        response = client.get(url)

        assert response.status_code == 200
        auth_url = response.json()["auth_url"]
        assert "accounts.google.com" in auth_url
        assert "test-client-id" in auth_url

    def test_get_login_url_github(self, client, settings):
        """Test getting GitHub OAuth URL."""
        settings.GITHUB_CLIENT_ID = "test-github-id"

        url = reverse("auth-social-login", kwargs={"provider": "github"})
        response = client.get(url)

        assert response.status_code == 200
        auth_url = response.json()["auth_url"]
        assert "github.com" in auth_url
        assert "test-github-id" in auth_url


class TestSocialAccounts:
    """Test social account management."""

    def test_list_social_accounts_empty(self, authenticated_client, user):
        """Test listing when no social accounts."""
        url = reverse("social-accounts-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.json()["accounts"] == []

    def test_list_social_accounts(self, authenticated_client, user):
        """Test listing connected social accounts."""
        SocialAccount.objects.create(
            user=user,
            provider="google",
            provider_id="123456",
        )

        url = reverse("social-accounts-list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        accounts = response.json()["accounts"]
        assert len(accounts) == 1
        assert accounts[0]["provider"] == "google"

    def test_disconnect_social_account(self, authenticated_client, user):
        """Test disconnecting a social account."""
        # User has password set, so can disconnect
        account = SocialAccount.objects.create(
            user=user,
            provider="google",
            provider_id="123456",
        )

        url = reverse("social-account-disconnect", kwargs={"account_id": account.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 200
        assert not SocialAccount.objects.filter(id=account.id).exists()

    def test_cannot_disconnect_last_auth_method(self, authenticated_client, user):
        """Test cannot disconnect if it's the last auth method."""
        # Clear user's password
        user.local_profile.password_hash = ""
        user.local_profile.save()

        account = SocialAccount.objects.create(
            user=user,
            provider="google",
            provider_id="123456",
        )

        url = reverse("social-account-disconnect", kwargs={"account_id": account.id})
        response = authenticated_client.delete(url)

        assert response.status_code == 400
        assert "Cannot disconnect" in response.json()["error"]
        # Account should still exist
        assert SocialAccount.objects.filter(id=account.id).exists()


class TestSocialAccountModel:
    """Test SocialAccount model."""

    def test_create_social_account(self, user):
        """Test creating a social account."""
        account = SocialAccount.objects.create(
            user=user,
            provider="github",
            provider_id="12345",
        )

        assert account.provider == "github"
        assert account.provider_id == "12345"
        assert account.user == user

    def test_unique_constraint(self, user):
        """Test provider+provider_id is unique."""
        SocialAccount.objects.create(
            user=user,
            provider="google",
            provider_id="123",
        )

        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
        )

        # Same provider+id for different user should fail
        with pytest.raises(Exception):
            SocialAccount.objects.create(
                user=other_user,
                provider="google",
                provider_id="123",
            )

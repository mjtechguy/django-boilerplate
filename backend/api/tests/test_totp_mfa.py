"""
Tests for built-in TOTP MFA functionality.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from api.models_mfa import MFAToken, TOTPDevice

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """Create a test user with local profile."""
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


class TestMFASetup:
    """Test MFA setup flow."""

    def test_setup_returns_secret_and_qr(self, authenticated_client, user):
        """Test MFA setup returns secret and QR code."""
        url = reverse("auth-mfa-setup")
        response = authenticated_client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert len(data["secret"]) == 32  # Base32 secret
        assert "qr_code" in data
        assert data["qr_code"].startswith("data:image/png;base64,")
        assert "provisioning_uri" in data
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10

    def test_setup_creates_unconfirmed_device(self, authenticated_client, user):
        """Test setup creates unconfirmed device."""
        url = reverse("auth-mfa-setup")
        authenticated_client.post(url)

        device = TOTPDevice.objects.get(user=user)
        assert device.confirmed is False

    def test_setup_replaces_unconfirmed_device(self, authenticated_client, user):
        """Test new setup replaces existing unconfirmed device."""
        url = reverse("auth-mfa-setup")
        authenticated_client.post(url)
        old_device = TOTPDevice.objects.get(user=user)
        old_secret = old_device.secret

        authenticated_client.post(url)
        new_device = TOTPDevice.objects.get(user=user)

        assert new_device.secret != old_secret
        assert TOTPDevice.objects.filter(user=user).count() == 1

    def test_setup_fails_if_mfa_enabled(self, authenticated_client, user):
        """Test cannot setup MFA if already enabled."""
        TOTPDevice.objects.create_device(user=user)
        device = TOTPDevice.objects.get(user=user)
        device.confirmed = True
        device.save()

        url = reverse("auth-mfa-setup")
        response = authenticated_client.post(url)

        assert response.status_code == 400
        assert "already enabled" in response.json()["error"]


class TestMFAConfirm:
    """Test MFA confirmation."""

    def test_confirm_with_valid_code(self, authenticated_client, user):
        """Test confirming MFA with valid TOTP code."""
        # Setup MFA first
        device, _ = TOTPDevice.objects.create_device(user=user)

        # Get valid code
        code = device.get_totp().now()

        url = reverse("auth-mfa-confirm")
        response = authenticated_client.post(url, {"code": code})

        assert response.status_code == 200
        device.refresh_from_db()
        assert device.confirmed is True

    def test_confirm_with_invalid_code(self, authenticated_client, user):
        """Test confirming with invalid code fails."""
        TOTPDevice.objects.create_device(user=user)

        url = reverse("auth-mfa-confirm")
        response = authenticated_client.post(url, {"code": "000000"})

        assert response.status_code == 400
        assert "Invalid" in response.json()["error"]

    def test_confirm_without_setup(self, authenticated_client, user):
        """Test confirm fails if no pending setup."""
        url = reverse("auth-mfa-confirm")
        response = authenticated_client.post(url, {"code": "123456"})

        assert response.status_code == 400
        assert "pending" in response.json()["error"]


class TestMFADisable:
    """Test MFA disable."""

    def test_disable_with_valid_code(self, authenticated_client, user):
        """Test disabling MFA with valid TOTP code."""
        device, _ = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        code = device.get_totp().now()

        url = reverse("auth-mfa-disable")
        response = authenticated_client.post(url, {"code": code})

        assert response.status_code == 200
        assert not TOTPDevice.objects.filter(user=user).exists()

    def test_disable_with_backup_code(self, authenticated_client, user):
        """Test disabling MFA with backup code."""
        device, backup_codes = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        url = reverse("auth-mfa-disable")
        response = authenticated_client.post(url, {"code": backup_codes[0]})

        assert response.status_code == 200
        assert not TOTPDevice.objects.filter(user=user).exists()

    def test_disable_without_mfa(self, authenticated_client, user):
        """Test disable fails if MFA not enabled."""
        url = reverse("auth-mfa-disable")
        response = authenticated_client.post(url, {"code": "123456"})

        assert response.status_code == 400
        assert "not enabled" in response.json()["error"]


class TestMFAStatus:
    """Test MFA status endpoint."""

    def test_status_disabled(self, authenticated_client, user):
        """Test status shows disabled when MFA not enabled."""
        url = reverse("auth-mfa-status")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_status_enabled(self, authenticated_client, user):
        """Test status shows enabled when MFA configured."""
        device, _ = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        url = reverse("auth-mfa-status")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["backup_codes_remaining"] == 10


class TestMFABackupCodes:
    """Test backup code regeneration."""

    def test_regenerate_backup_codes(self, authenticated_client, user):
        """Test regenerating backup codes."""
        device, old_codes = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        code = device.get_totp().now()

        url = reverse("auth-mfa-backup-codes")
        response = authenticated_client.post(url, {"code": code})

        assert response.status_code == 200
        new_codes = response.json()["backup_codes"]
        assert len(new_codes) == 10
        assert new_codes != old_codes


class TestMFALoginFlow:
    """Test MFA during login."""

    def test_login_with_mfa_returns_mfa_token(self, client, user):
        """Test login with MFA enabled returns MFA token."""
        device, _ = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        url = reverse("auth-login")
        response = client.post(url, {
            "email": "test@example.com",
            "password": "TestPass123!",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["mfa_required"] is True
        assert "mfa_token" in data

    def test_login_without_mfa_returns_tokens(self, client, user):
        """Test login without MFA returns JWT tokens directly."""
        url = reverse("auth-login")
        response = client.post(url, {
            "email": "test@example.com",
            "password": "TestPass123!",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "mfa_required" not in data

    def test_mfa_verify_with_valid_code(self, client, user):
        """Test completing MFA verification."""
        device, _ = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        # Get MFA token from login
        login_url = reverse("auth-login")
        login_response = client.post(login_url, {
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        mfa_token = login_response.json()["mfa_token"]

        # Complete MFA
        code = device.get_totp().now()
        verify_url = reverse("auth-mfa-verify")
        response = client.post(verify_url, {
            "mfa_token": mfa_token,
            "code": code,
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_mfa_verify_with_backup_code(self, client, user):
        """Test completing MFA with backup code."""
        device, backup_codes = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        # Get MFA token
        login_url = reverse("auth-login")
        login_response = client.post(login_url, {
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        mfa_token = login_response.json()["mfa_token"]

        # Complete MFA with backup code
        verify_url = reverse("auth-mfa-verify")
        response = client.post(verify_url, {
            "mfa_token": mfa_token,
            "code": backup_codes[0],
        })

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_mfa_verify_with_invalid_code(self, client, user):
        """Test MFA verification fails with invalid code."""
        device, _ = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        # Get MFA token
        login_url = reverse("auth-login")
        login_response = client.post(login_url, {
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        mfa_token = login_response.json()["mfa_token"]

        # Try invalid code
        verify_url = reverse("auth-mfa-verify")
        response = client.post(verify_url, {
            "mfa_token": mfa_token,
            "code": "000000",
        })

        assert response.status_code == 401

    def test_mfa_token_expires(self, client, user):
        """Test expired MFA token is rejected."""
        from django.utils import timezone
        import datetime

        device, _ = TOTPDevice.objects.create_device(user=user)
        device.confirmed = True
        device.save()

        # Create expired MFA token
        mfa_token = MFAToken.objects.create(
            user=user,
            token="test-token-123",
            expires_at=timezone.now() - datetime.timedelta(minutes=10),
        )

        # Try to verify with expired token
        code = device.get_totp().now()
        verify_url = reverse("auth-mfa-verify")
        response = client.post(verify_url, {
            "mfa_token": mfa_token.token,
            "code": code,
        })

        assert response.status_code == 401
        assert "expired" in response.json()["error"]


class TestTOTPDevice:
    """Test TOTPDevice model."""

    def test_verify_valid_code(self, user):
        """Test TOTP code verification."""
        device, _ = TOTPDevice.objects.create_device(user=user)
        code = device.get_totp().now()

        assert device.verify_code(code) is True

    def test_verify_invalid_code(self, user):
        """Test invalid code is rejected."""
        device, _ = TOTPDevice.objects.create_device(user=user)

        assert device.verify_code("000000") is False

    def test_backup_code_is_consumed(self, user):
        """Test backup code can only be used once."""
        device, backup_codes = TOTPDevice.objects.create_device(user=user)
        code = backup_codes[0]

        assert device.verify_backup_code(code) is True
        assert device.verify_backup_code(code) is False
        assert device.remaining_backup_codes() == 9

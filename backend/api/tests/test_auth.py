import pytest
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_auth_cache(monkeypatch):
    # Clear JWKS cache before each test
    from api import auth

    auth._jwks_cache.cache_clear()  # noqa: SLF001
    yield


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def mock_auth(monkeypatch):
    """
    Patch KeycloakJWTAuthentication._validate_token to bypass JWKS calls.
    """

    def _mock_validate(self, token):
        return {
            "sub": "user-123",
            "email": "user@example.com",
            "realm_roles": ["platform_admin"],
            "client_roles": ["org_admin"],
        }

    monkeypatch.setattr("api.auth.KeycloakJWTAuthentication._validate_token", _mock_validate)
    return _mock_validate


def test_auth_ping_ok(client, mock_auth):
    resp = client.get(
        reverse("api-ping"),
        HTTP_AUTHORIZATION="Bearer test-token",
    )
    assert resp.status_code == 200
    assert resp.json()["claims_sub"] == "user-123"


def test_auth_ping_missing_token_unauthorized(client):
    resp = client.get(reverse("api-ping"))
    assert resp.status_code == 401

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_idempotency_blocks_duplicate(client, monkeypatch):
    # Bypass auth for this test
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token", lambda self, t: {"sub": "u"}
    )
    key = "dup-key"
    url = reverse("api-ping")
    resp1 = client.post(url, HTTP_AUTHORIZATION="Bearer x", HTTP_IDEMPOTENCY_KEY=key)
    assert resp1.status_code == 200
    resp2 = client.post(url, HTTP_AUTHORIZATION="Bearer x", HTTP_IDEMPOTENCY_KEY=key)
    assert resp2.status_code == 409
    assert resp2.json()["idempotency_key"] == key


def test_idempotency_allows_different_keys(client, monkeypatch):
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token", lambda self, t: {"sub": "u"}
    )
    url = reverse("api-ping")
    resp1 = client.post(url, HTTP_AUTHORIZATION="Bearer x", HTTP_IDEMPOTENCY_KEY="k1")
    resp2 = client.post(url, HTTP_AUTHORIZATION="Bearer x", HTTP_IDEMPOTENCY_KEY="k2")
    assert resp1.status_code == 200
    assert resp2.status_code == 200

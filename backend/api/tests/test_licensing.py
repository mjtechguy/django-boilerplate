import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import Org

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def _auth(monkeypatch, org_id, roles):
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token",
        lambda self, t: {
            "sub": "u",
            "org_id": str(org_id),
            "client_roles": roles,
            "realm_roles": [],
        },
    )


def test_get_license_allowed(monkeypatch, client):
    org = Org.objects.create(name="Acme")
    _auth(monkeypatch, org.id, ["org_admin"])
    url = reverse("org-license", kwargs={"org_id": org.id})
    resp = client.get(url, HTTP_AUTHORIZATION="Bearer x")
    assert resp.status_code == 200
    body = resp.json()
    assert body["license_tier"] == "free"


def test_update_license(monkeypatch, client):
    org = Org.objects.create(name="Acme")
    _auth(monkeypatch, org.id, ["org_admin"])
    url = reverse("org-license", kwargs={"org_id": org.id})
    resp = client.put(
        url,
        {"license_tier": "pro", "feature_flags": {"export": True}},
        format="json",
        HTTP_AUTHORIZATION="Bearer x",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["license_tier"] == "pro"
    assert body["feature_flags"]["export"] is True


def test_license_forbidden(monkeypatch, client):
    org = Org.objects.create(name="Acme")
    _auth(monkeypatch, org.id, ["org_member"])
    url = reverse("org-license", kwargs={"org_id": org.id})
    resp = client.get(url, HTTP_AUTHORIZATION="Bearer x")
    assert resp.status_code == 403


def test_stripe_webhook_records_status(client):
    org = Org.objects.create(name="Acme")
    url = reverse("stripe-webhook")
    resp = client.post(url, {"org_id": str(org.id), "status": "synced"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["received"] is True

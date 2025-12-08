import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import Org

pytestmark = pytest.mark.django_db


def _auth(monkeypatch, roles):
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token",
        lambda self, t: {"sub": "u", "realm_roles": roles, "client_roles": [], "org_id": None},
    )


def test_admin_org_list_allows_platform_admin(monkeypatch):
    Org.objects.create(name="Acme")
    _auth(monkeypatch, ["platform_admin"])
    client = APIClient()
    resp = client.get(reverse("admin-org-list"), HTTP_AUTHORIZATION="Bearer x")
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_admin_org_list_forbidden_for_org_admin(monkeypatch):
    Org.objects.create(name="Acme")
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token",
        lambda self, t: {
            "sub": "u",
            "realm_roles": [],
            "client_roles": ["org_admin"],
            "org_id": None,
        },
    )
    client = APIClient()
    resp = client.get(reverse("admin-org-list"), HTTP_AUTHORIZATION="Bearer x")
    assert resp.status_code == 403

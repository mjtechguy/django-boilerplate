from types import SimpleNamespace

import pytest
from cerbos.sdk.model import Effect
from django.urls import reverse
from rest_framework.test import APIClient

from api import cerbos_client

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_protected_allows_when_cerbos_allows(monkeypatch, client):
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token",
        lambda self, t: {"sub": "u", "realm_roles": [], "client_roles": [], "org_id": "org-123"},
    )
    monkeypatch.setattr(
        "api.permissions.check_action",
        lambda principal_id,
        roles,
        principal_attrs,
        resource_kind,
        resource_id,
        resource_attrs,
        action: True,
    )
    url = reverse("api-protected")
    resp = client.get(
        url,
        HTTP_AUTHORIZATION="Bearer x",
        HTTP_X_REQUEST_ID="req1",
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "protected-ok"


def test_protected_denies_when_cerbos_denies(monkeypatch, client):
    monkeypatch.setattr(
        "api.auth.KeycloakJWTAuthentication._validate_token",
        lambda self, t: {"sub": "u", "realm_roles": [], "client_roles": [], "org_id": "org-123"},
    )
    monkeypatch.setattr(
        "api.permissions.check_action",
        lambda principal_id,
        roles,
        principal_attrs,
        resource_kind,
        resource_id,
        resource_attrs,
        action: False,
    )
    url = reverse("api-protected")
    resp = client.get(
        url,
        HTTP_AUTHORIZATION="Bearer x",
        HTTP_X_REQUEST_ID="req1",
    )
    assert resp.status_code == 403


def test_cerbos_decision_cache(monkeypatch):
    calls = {"count": 0}

    class FakeClient:
        def check_resources(self, principal, resources):
            calls["count"] += 1
            return SimpleNamespace(results=[SimpleNamespace(actions={"read": Effect.ALLOW})])

    # Save original function to restore LRU cache behavior after test
    original_get_client = cerbos_client.get_client
    cerbos_client.get_client.cache_clear()
    monkeypatch.setattr("api.cerbos_client.get_client", lambda: FakeClient())

    try:
        principal_id = "u1"
        roles = {"org_admin"}
        principal_attrs = {"org_id": "org-1"}
        resource_attrs = {"org_id": "org-1"}
        # First call hits fake client
        allowed1 = cerbos_client.check_action(
            principal_id, roles, principal_attrs, "sample_resource", "1", resource_attrs, "read"
        )
        allowed2 = cerbos_client.check_action(
            principal_id, roles, principal_attrs, "sample_resource", "1", resource_attrs, "read"
        )
        assert allowed1 is True and allowed2 is True
        assert calls["count"] == 1  # cached

        cerbos_client.invalidate_decision_cache()
        allowed3 = cerbos_client.check_action(
            principal_id, roles, principal_attrs, "sample_resource", "1", resource_attrs, "read"
        )
        assert allowed3 is True
        assert calls["count"] == 2
    finally:
        # Cleanup: clear decision cache and restore get_client for subsequent tests
        cerbos_client.invalidate_decision_cache()
        # Clear the LRU cache on the original function
        original_get_client.cache_clear()

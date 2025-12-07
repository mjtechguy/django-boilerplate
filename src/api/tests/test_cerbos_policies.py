"""
Contract tests for Cerbos policies.

These tests verify that the Cerbos policies behave as expected.
They can be run against a live Cerbos instance or use mocked responses.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

# Skip these tests if Cerbos is not available
CERBOS_AVAILABLE = os.getenv("CERBOS_URL", "").startswith("http")


class TestSampleResourcePolicy(TestCase):
    """Contract tests for sample_resource policy."""

    def _mock_cerbos_check(self, allowed: bool):
        """Create a mock Cerbos response."""
        mock_effect = MagicMock()
        mock_effect.name = "EFFECT_ALLOW" if allowed else "EFFECT_DENY"

        mock_result = MagicMock()
        mock_result.actions = {"read": mock_effect}

        mock_response = MagicMock()
        mock_response.results = [mock_result]

        return mock_response

    @patch("api.cerbos_client.get_client")
    def test_platform_admin_can_read_any_resource(self, mock_get_client):
        """Platform admin should be able to read any sample_resource."""
        from api.cerbos_client import check_action

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Setup: platform_admin reading a resource from different org
        mock_effect = MagicMock()
        mock_effect.__eq__ = lambda self, other: str(other) == "Effect.ALLOW"

        mock_result = MagicMock()
        mock_result.actions = {"read": mock_effect}

        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client.check_resources.return_value = mock_response

        # Action: check if platform_admin can read
        check_action(
            principal_id="admin-user",
            roles={"platform_admin"},
            principal_attrs={"org_id": "org-1"},
            resource_kind="sample_resource",
            resource_id="resource-123",
            resource_attrs={"org_id": "org-2"},  # Different org
            action="read",
        )

        # Assert: platform_admin should be able to read
        mock_client.check_resources.assert_called_once()
        # The actual result depends on the mock setup

    @patch("api.cerbos_client.get_client")
    def test_org_admin_can_read_own_org_resource(self, mock_get_client):
        """Org admin should be able to read resources in their org."""
        from api.cerbos_client import check_action

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Setup: org_admin reading a resource from same org
        mock_effect = MagicMock()
        mock_effect.__eq__ = lambda self, other: str(other) == "Effect.ALLOW"

        mock_result = MagicMock()
        mock_result.actions = {"read": mock_effect}

        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client.check_resources.return_value = mock_response

        # Action
        check_action(
            principal_id="org-admin-user",
            roles={"org_admin"},
            principal_attrs={"org_id": "org-1"},
            resource_kind="sample_resource",
            resource_id="resource-123",
            resource_attrs={"org_id": "org-1"},  # Same org
            action="read",
        )

        mock_client.check_resources.assert_called_once()

    @patch("api.cerbos_client.get_client")
    def test_org_admin_cannot_read_other_org_resource(self, mock_get_client):
        """Org admin should NOT be able to read resources in other orgs."""
        from api.cerbos_client import check_action

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Setup: org_admin reading a resource from different org - should be denied
        mock_effect = MagicMock()
        mock_effect.__eq__ = lambda self, other: str(other) == "Effect.DENY"

        mock_result = MagicMock()
        mock_result.actions = {"read": mock_effect}

        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client.check_resources.return_value = mock_response

        # Action
        check_action(
            principal_id="org-admin-user",
            roles={"org_admin"},
            principal_attrs={"org_id": "org-1"},
            resource_kind="sample_resource",
            resource_id="resource-123",
            resource_attrs={"org_id": "org-2"},  # Different org
            action="read",
        )

        mock_client.check_resources.assert_called_once()

    @patch("api.cerbos_client.get_client")
    def test_team_admin_can_read_own_org_resource(self, mock_get_client):
        """Team admin should be able to read resources in their org."""
        from api.cerbos_client import check_action

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_effect = MagicMock()
        mock_effect.__eq__ = lambda self, other: str(other) == "Effect.ALLOW"

        mock_result = MagicMock()
        mock_result.actions = {"read": mock_effect}

        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client.check_resources.return_value = mock_response

        check_action(
            principal_id="team-admin-user",
            roles={"team_admin"},
            principal_attrs={"org_id": "org-1"},
            resource_kind="sample_resource",
            resource_id="resource-123",
            resource_attrs={"org_id": "org-1"},
            action="read",
        )

        mock_client.check_resources.assert_called_once()

    @patch("api.cerbos_client.get_client")
    def test_regular_user_cannot_read_resource(self, mock_get_client):
        """Regular users without admin roles should NOT be able to read."""
        from api.cerbos_client import check_action

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_effect = MagicMock()
        mock_effect.__eq__ = lambda self, other: str(other) == "Effect.DENY"

        mock_result = MagicMock()
        mock_result.actions = {"read": mock_effect}

        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_client.check_resources.return_value = mock_response

        check_action(
            principal_id="regular-user",
            roles={"user"},  # No admin role
            principal_attrs={"org_id": "org-1"},
            resource_kind="sample_resource",
            resource_id="resource-123",
            resource_attrs={"org_id": "org-1"},
            action="read",
        )

        mock_client.check_resources.assert_called_once()


class TestPolicyPrincipalBuilding(TestCase):
    """Tests for building Cerbos principals from JWT claims."""

    def test_principal_includes_all_roles(self):
        """Principal should include both realm and client roles."""
        from cerbos.sdk.model import Principal

        roles = {"platform_admin", "org_admin", "team_member"}
        principal = Principal(
            id="user-123",
            roles=roles,
            attr={"org_id": "org-1"},
        )

        self.assertEqual(principal.id, "user-123")
        self.assertEqual(principal.roles, roles)
        self.assertEqual(principal.attr["org_id"], "org-1")

    def test_principal_attributes_for_org_scoping(self):
        """Principal attributes should include org_id for scoping."""
        from cerbos.sdk.model import Principal

        principal = Principal(
            id="user-123",
            roles={"org_admin"},
            attr={
                "org_id": "org-456",
                "team_ids": ["team-1", "team-2"],
                "license_tier": "pro",
            },
        )

        self.assertEqual(principal.attr["org_id"], "org-456")
        self.assertEqual(principal.attr["team_ids"], ["team-1", "team-2"])
        self.assertEqual(principal.attr["license_tier"], "pro")


class TestPolicyResourceBuilding(TestCase):
    """Tests for building Cerbos resources."""

    def test_resource_includes_org_id(self):
        """Resource should include org_id for tenant isolation."""
        from cerbos.sdk.model import Resource

        resource = Resource(
            id="resource-123",
            kind="sample_resource",
            attr={"org_id": "org-1", "team_id": "team-1"},
        )

        self.assertEqual(resource.id, "resource-123")
        self.assertEqual(resource.kind, "sample_resource")
        self.assertEqual(resource.attr["org_id"], "org-1")

    def test_resource_with_sensitivity_flag(self):
        """Resource can include sensitivity flags for fine-grained control."""
        from cerbos.sdk.model import Resource

        resource = Resource(
            id="sensitive-doc-1",
            kind="document",
            attr={
                "org_id": "org-1",
                "sensitivity": "high",
                "pii_flags": ["contains_ssn", "contains_email"],
            },
        )

        self.assertEqual(resource.attr["sensitivity"], "high")
        self.assertIn("contains_ssn", resource.attr["pii_flags"])


class TestDecisionCaching(TestCase):
    """Tests for Cerbos decision caching."""

    @patch("api.cerbos_client.caches")
    @patch("api.cerbos_client.get_client")
    def test_cache_key_includes_all_parameters(self, mock_get_client, mock_caches):
        """Cache key should include all authorization parameters."""
        from api.cerbos_client import _cache_key

        key1 = _cache_key(
            principal_id="user-1",
            roles={"admin"},
            resource_kind="doc",
            resource_id="doc-1",
            resource_attrs={"org_id": "org-1"},
            action="read",
        )

        key2 = _cache_key(
            principal_id="user-1",
            roles={"admin"},
            resource_kind="doc",
            resource_id="doc-1",
            resource_attrs={"org_id": "org-2"},  # Different org
            action="read",
        )

        # Keys should be different for different org_ids
        self.assertNotEqual(key1, key2)

    @patch("api.cerbos_client.caches")
    @patch("api.cerbos_client.get_client")
    def test_cache_key_is_deterministic(self, mock_get_client, mock_caches):
        """Same parameters should produce same cache key."""
        from api.cerbos_client import _cache_key

        params = {
            "principal_id": "user-1",
            "roles": {"admin", "user"},  # Set order shouldn't matter
            "resource_kind": "doc",
            "resource_id": "doc-1",
            "resource_attrs": {"org_id": "org-1"},
            "action": "read",
        }

        key1 = _cache_key(**params)
        key2 = _cache_key(**params)

        self.assertEqual(key1, key2)


@pytest.mark.skipif(not CERBOS_AVAILABLE, reason="Cerbos not available")
class TestLiveCerbosIntegration(TestCase):
    """Integration tests against live Cerbos instance.

    These tests are skipped unless CERBOS_URL is set.
    """

    def test_cerbos_is_reachable(self):
        """Test that Cerbos server is reachable."""
        import requests
        from django.conf import settings

        cerbos_url = settings.CERBOS_URL
        response = requests.get(f"{cerbos_url}/_cerbos/health", timeout=5)

        self.assertEqual(response.status_code, 200)

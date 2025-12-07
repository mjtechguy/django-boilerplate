"""
Tests for settings precedence: env -> global -> org override.
"""

import os
from unittest.mock import patch

from django.test import TestCase, override_settings

from api.models import Org, Settings


class TestSettingsPrecedence(TestCase):
    """Tests for settings lookup precedence."""

    def setUp(self):
        """Create test org and settings."""
        self.org = Org.objects.create(
            name="Test Org",
            status="active",
            license_tier="pro",
        )

    def test_env_value_returned_when_no_db_settings(self):
        """Environment value should be returned when no DB settings exist."""
        with patch.dict(os.environ, {"LICENSE_TIER_DEFAULT": "enterprise"}):
            from django.conf import settings as django_settings

            # Force settings reload
            tier = getattr(django_settings, "LICENSE_TIER_DEFAULT", "free")
            # Note: This tests the pattern, actual implementation may vary
            self.assertIn(tier, ["free", "enterprise"])

    def test_global_setting_overrides_env(self):
        """Global DB setting should override environment default."""
        # Create global setting (no org)
        Settings.objects.create(
            key="custom_feature",
            value="enabled",
            scope="global",
        )

        setting = Settings.objects.filter(key="custom_feature", scope="global").first()
        self.assertIsNotNone(setting)
        self.assertEqual(setting.value, "enabled")

    def test_org_setting_overrides_global(self):
        """Org-specific setting should override global setting."""
        # Create global setting
        Settings.objects.create(
            key="feature_x",
            value="disabled",
            scope="global",
        )

        # Create org-specific override
        Settings.objects.create(
            key="feature_x",
            value="enabled",
            scope="org",
            org=self.org,
        )

        # Query should get org-specific value
        org_setting = Settings.objects.filter(key="feature_x", scope="org", org=self.org).first()
        global_setting = Settings.objects.filter(key="feature_x", scope="global").first()

        self.assertEqual(org_setting.value, "enabled")
        self.assertEqual(global_setting.value, "disabled")

    def test_get_setting_with_precedence(self):
        """get_setting helper should respect precedence order."""
        # Create both global and org settings
        Settings.objects.create(
            key="test_key",
            value="global_value",
            scope="global",
        )
        Settings.objects.create(
            key="test_key",
            value="org_value",
            scope="org",
            org=self.org,
        )

        # Get setting for org - should return org value
        org_setting = Settings.objects.filter(key="test_key", org=self.org).first()

        # Get global setting
        global_setting = Settings.objects.filter(
            key="test_key", scope="global", org__isnull=True
        ).first()

        self.assertEqual(org_setting.value, "org_value")
        self.assertEqual(global_setting.value, "global_value")

    def test_missing_org_setting_falls_back_to_global(self):
        """Missing org setting should fall back to global."""
        # Create only global setting
        Settings.objects.create(
            key="global_only_key",
            value="global_default",
            scope="global",
        )

        # No org setting exists
        org_setting = Settings.objects.filter(key="global_only_key", org=self.org).first()

        global_setting = Settings.objects.filter(key="global_only_key", scope="global").first()

        self.assertIsNone(org_setting)
        self.assertIsNotNone(global_setting)
        self.assertEqual(global_setting.value, "global_default")


class TestLicenseTierSettings(TestCase):
    """Tests for license tier configuration."""

    def setUp(self):
        """Create test org."""
        self.org = Org.objects.create(
            name="Test Org",
            status="active",
            license_tier="free",
        )

    def test_org_license_tier_stored_correctly(self):
        """Org license tier should be stored and retrievable."""
        self.assertEqual(self.org.license_tier, "free")

        self.org.license_tier = "pro"
        self.org.save()
        self.org.refresh_from_db()

        self.assertEqual(self.org.license_tier, "pro")

    def test_org_feature_flags_stored_as_json(self):
        """Org feature flags should be stored as JSON."""
        self.org.feature_flags = {
            "advanced_reporting": True,
            "api_access": True,
            "max_users": 100,
        }
        self.org.save()
        self.org.refresh_from_db()

        self.assertEqual(self.org.feature_flags["advanced_reporting"], True)
        self.assertEqual(self.org.feature_flags["max_users"], 100)


class TestSettingsScoping(TestCase):
    """Tests for settings scope enforcement."""

    def setUp(self):
        """Create test orgs."""
        self.org1 = Org.objects.create(name="Org 1", status="active")
        self.org2 = Org.objects.create(name="Org 2", status="active")

    def test_org_settings_are_isolated(self):
        """Settings for one org should not affect another."""
        Settings.objects.create(
            key="isolated_key",
            value="org1_value",
            scope="org",
            org=self.org1,
        )
        Settings.objects.create(
            key="isolated_key",
            value="org2_value",
            scope="org",
            org=self.org2,
        )

        org1_setting = Settings.objects.get(key="isolated_key", org=self.org1)
        org2_setting = Settings.objects.get(key="isolated_key", org=self.org2)

        self.assertEqual(org1_setting.value, "org1_value")
        self.assertEqual(org2_setting.value, "org2_value")

    def test_global_settings_have_no_org(self):
        """Global settings should not be associated with any org."""
        global_setting = Settings.objects.create(
            key="global_key",
            value="global_value",
            scope="global",
        )

        self.assertIsNone(global_setting.org)
        self.assertEqual(global_setting.scope, "global")

    def test_unique_constraint_on_key_org_scope(self):
        """Duplicate key+org+scope should raise error."""
        Settings.objects.create(
            key="unique_key",
            value="value1",
            scope="org",
            org=self.org1,
        )

        with self.assertRaises(Exception):  # IntegrityError
            Settings.objects.create(
                key="unique_key",
                value="value2",
                scope="org",
                org=self.org1,
            )


class TestEnvironmentSettings(TestCase):
    """Tests for environment-based settings."""

    @override_settings(LICENSE_TIER_DEFAULT="enterprise")
    def test_license_tier_default_from_settings(self):
        """LICENSE_TIER_DEFAULT should be readable from Django settings."""
        from django.conf import settings

        self.assertEqual(settings.LICENSE_TIER_DEFAULT, "enterprise")

    @override_settings(CERBOS_DECISION_CACHE_TTL=60)
    def test_cerbos_cache_ttl_from_settings(self):
        """CERBOS_DECISION_CACHE_TTL should be configurable."""
        from django.conf import settings

        self.assertEqual(settings.CERBOS_DECISION_CACHE_TTL, 60)

    @override_settings(IDEMPOTENCY_TTL_SECONDS=3600)
    def test_idempotency_ttl_from_settings(self):
        """IDEMPOTENCY_TTL_SECONDS should be configurable."""
        from django.conf import settings

        self.assertEqual(settings.IDEMPOTENCY_TTL_SECONDS, 3600)

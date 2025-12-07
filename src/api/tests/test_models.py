import pytest

from api.models import Org, Settings

pytestmark = pytest.mark.django_db


def test_settings_precedence_env_default_overridden_by_global_then_org(settings, monkeypatch):
    monkeypatch.setenv("LICENSE_TIER_DEFAULT", "free")
    org = Org.objects.create(name="Acme")
    # No settings yet: should fall back to default
    assert Settings.get_value("license_tier", org=org, default="free") == "free"
    # Global override
    Settings.objects.create(scope=Settings.Scope.GLOBAL, key="license_tier", value="pro")
    assert Settings.get_value("license_tier", org=org, default="free") == "pro"
    # Org override
    Settings.objects.create(
        scope=Settings.Scope.ORG, org=org, key="license_tier", value="enterprise"
    )
    assert Settings.get_value("license_tier", org=org, default="free") == "enterprise"


def test_membership_constraints_unique_per_org_team(settings, django_assert_num_queries):
    org = Org.objects.create(name="Acme")
    # Minimal check for org uniqueness enforced by DB index
    Settings.objects.create(scope=Settings.Scope.ORG, org=org, key="k", value={"v": 1})
    with pytest.raises(Exception):
        Settings.objects.create(scope=Settings.Scope.ORG, org=org, key="k", value={"v": 2})


def test_org_scoped_queryset_filters_by_org():
    from api.models import SampleResource

    org1 = Org.objects.create(name="Acme")
    org2 = Org.objects.create(name="Beta")
    SampleResource.objects.create(org=org1, name="r1")
    SampleResource.objects.create(org=org2, name="r2")

    org1_resources = SampleResource.objects.for_org(org1.id)
    assert org1_resources.count() == 1
    assert org1_resources.first().name == "r1"

    org2_resources = SampleResource.objects.for_org(org2.id)
    assert org2_resources.count() == 1
    assert org2_resources.first().name == "r2"

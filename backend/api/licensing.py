import json
from typing import Dict

from django.conf import settings
from django.utils import timezone

from api.cerbos_client import invalidate_decision_cache
from api.models import Org, Settings


def get_license(org: Org) -> Dict:
    tier = Settings.get_value("license_tier", org=org, default=settings.LICENSE_TIER_DEFAULT)
    flags = Settings.get_value(
        "feature_flags", org=org, default=settings.LICENSE_FEATURE_FLAGS_DEFAULT
    )
    if isinstance(flags, str):
        try:
            flags = json.loads(flags)
        except Exception:  # noqa: BLE001
            flags = {}
    return {"license_tier": tier, "feature_flags": flags}


def update_license(org: Org, tier: str, feature_flags: Dict) -> Dict:
    Settings.objects.update_or_create(
        scope=Settings.Scope.ORG,
        org=org,
        key="license_tier",
        defaults={"value": tier},
    )
    Settings.objects.update_or_create(
        scope=Settings.Scope.ORG,
        org=org,
        key="feature_flags",
        defaults={"value": feature_flags},
    )
    org.license_tier = tier
    org.feature_flags = feature_flags
    org.save(update_fields=["license_tier", "feature_flags", "updated_at"])
    invalidate_decision_cache()
    return {"license_tier": tier, "feature_flags": feature_flags}


def set_stripe_sync_status(org: Org, status: str, synced_at=None):
    Settings.objects.update_or_create(
        scope=Settings.Scope.ORG,
        org=org,
        key="stripe_sync_status",
        defaults={
            "value": {"status": status, "synced_at": synced_at or timezone.now().isoformat()}
        },
    )

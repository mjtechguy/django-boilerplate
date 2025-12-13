import json
from typing import Dict

from django.conf import settings
from django.utils import timezone

from api.cerbos_client import invalidate_decision_cache
from api.models import Org, Settings

# Import Division model for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api.models import Division, Team


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


def get_effective_license(org: Org, division=None, team=None) -> Dict:
    """
    Resolve effective license tier with bidirectional override.

    Priority: Division override → Org base
    Each level can override up OR down.

    Args:
        org: The Org instance
        division: Optional Division instance
        team: Optional Team instance (for future team-level features)

    Returns:
        dict with 'license_tier' and 'features' keys
    """
    # Get tier features from settings
    tier_features = getattr(settings, "STRIPE_TIER_FEATURES", {})

    # Start with org tier
    base_tier = org.license_tier or "free"
    base_features = tier_features.get(base_tier, tier_features.get("free", {})).copy()

    # Merge org feature_flags (can override tier defaults)
    effective_features = {**base_features, **(org.feature_flags or {})}
    effective_tier = base_tier

    # Apply division overrides
    if division:
        if division.billing_mode == "independent" and division.license_tier:
            # Division has independent billing - use its tier as base
            effective_tier = division.license_tier
            division_tier_features = tier_features.get(effective_tier, tier_features.get("free", {})).copy()
            effective_features = {**division_tier_features}

        # Merge division feature_flags (can go up or down)
        if division.feature_flags:
            effective_features = {**effective_features, **division.feature_flags}

    # Team-level feature overrides could be added here in the future
    # if team and hasattr(team, 'feature_flags') and team.feature_flags:
    #     effective_features = {**effective_features, **team.feature_flags}

    return {
        "license_tier": effective_tier,
        "features": effective_features,
    }


def get_division_license(division) -> Dict:
    """
    Get license info for a specific division.
    Resolves based on billing_mode (inherit vs independent).

    Args:
        division: Division instance

    Returns:
        dict with 'license_tier' and 'features' keys
    """
    org = division.org
    return get_effective_license(org, division=division)

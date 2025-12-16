import functools
import hashlib
import json
from typing import Any, Dict, Set

from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Effect, Principal, Resource, ResourceAction, ResourceList
from django.conf import settings
from django.core.cache import caches

# Use isolated cache for Cerbos decisions
CERBOS_CACHE_ALIAS = "cerbos"
DECISION_CACHE_PREFIX = "decision:"


@functools.lru_cache(maxsize=1)
def get_client() -> CerbosClient:
    """
    Get Cerbos client with TLS verification based on settings.

    In production, CERBOS_TLS_VERIFY should be True.
    If CERBOS_CA_BUNDLE is set, it will be used as the CA bundle path.
    """
    tls_verify = getattr(settings, "CERBOS_TLS_VERIFY", not settings.DEBUG)
    ca_bundle = getattr(settings, "CERBOS_CA_BUNDLE", "")

    # If CA bundle is specified and TLS is enabled, use it
    if tls_verify and ca_bundle:
        return CerbosClient(settings.CERBOS_URL, tls_verify=ca_bundle)
    return CerbosClient(settings.CERBOS_URL, tls_verify=tls_verify)


def _cache_key(
    principal_id: str,
    roles: Set[str],
    resource_kind: str,
    resource_id: str,
    resource_attrs: Dict,
    action: str,
) -> str:
    payload = {
        "principal_id": principal_id,
        "roles": sorted(roles),
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "resource_attrs": resource_attrs,
        "action": action,
    }
    hashed = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{DECISION_CACHE_PREFIX}{hashed}"


def check_action(
    principal_id: str,
    roles: Set[str],
    principal_attrs: Dict[str, Any],
    resource_kind: str,
    resource_id: str,
    resource_attrs: Dict[str, Any],
    action: str,
) -> bool:
    cache_ttl = getattr(settings, "CERBOS_DECISION_CACHE_TTL", 0)
    # Use isolated Cerbos cache for security, fall back to default if not configured
    try:
        cache = caches[CERBOS_CACHE_ALIAS]
    except Exception:
        cache = caches["default"]
    key = _cache_key(principal_id, roles, resource_kind, resource_id, resource_attrs, action)
    if cache_ttl > 0:
        cached = cache.get(key)
        if cached is not None:
            return cached

    client = get_client()

    principal = Principal(
        id=principal_id,
        roles=roles,
        attr=principal_attrs,
    )

    resource = Resource(
        id=resource_id,
        kind=resource_kind,
        attr=resource_attrs,
    )

    resources = ResourceList(resources=[ResourceAction(resource=resource, actions={action})])

    resp = client.check_resources(principal=principal, resources=resources)

    allowed = False
    if resp.results:
        result = resp.results[0]
        allowed = result.actions.get(action) == Effect.ALLOW

    if cache_ttl > 0:
        cache.set(key, allowed, timeout=cache_ttl)
    return allowed


def invalidate_decision_cache():
    """Clear Cerbos decision cache (coarse-grained)."""
    try:
        caches[CERBOS_CACHE_ALIAS].clear()
    except Exception:
        # Fall back to default cache if cerbos cache not configured
        # Note: Using clear() instead of delete_pattern for compatibility
        # with backends that don't support pattern deletion
        caches["default"].clear()

import functools
import hashlib
import json
from typing import Any, Dict, Set

from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Effect, Principal, Resource, ResourceAction, ResourceList
from django.conf import settings
from django.core.cache import caches

DECISION_CACHE_PREFIX = "cerbos:decision:"


@functools.lru_cache(maxsize=1)
def get_client() -> CerbosClient:
    return CerbosClient(settings.CERBOS_URL, tls_verify=False)


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
    """Clear decision cache (coarse-grained)."""
    caches["default"].clear()

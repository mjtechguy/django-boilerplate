"""
Per-tenant (organization) rate limiting for API endpoints.

This module implements organization-scoped throttling to prevent
any single tenant from consuming all API resources and to enforce
API quotas based on license tier.
"""

import time

from django.conf import settings
from django.core.cache import caches
from rest_framework.throttling import BaseThrottle

from api.models import Org


class OrgRateThrottle(BaseThrottle):
    """
    Throttle API requests per organization based on their license tier.

    Rate limits are determined by:
    1. Org's feature_flags['api_rate_limit'] if set
    2. Tier defaults from STRIPE_TIER_FEATURES
    3. Default 100/hour if org not found

    Unlimited (-1) means no throttling for that org.
    """

    cache = caches["idempotency"]
    cache_format = "throttle:org:%(ident)s"
    timer = time.time
    # Time window in seconds (1 hour)
    duration = 3600

    def allow_request(self, request, view):
        """
        Check if the request should be allowed based on org rate limit.

        Returns True if allowed, False if throttled.
        """
        # Get org_id from request
        org_id = self.get_org_id(request)

        if not org_id:
            # No org_id means no org-level throttling
            return True

        # Get rate limit for this org
        rate_limit = self.get_rate_limit(org_id)

        if rate_limit is None or rate_limit == -1:
            # Unlimited
            return True

        # Get cache key
        self.key = self.cache_format % {"ident": org_id}

        # Get current request history
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Remove old entries outside the time window
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        # Check if limit exceeded
        if len(self.history) >= rate_limit:
            return self.throttle_failure()

        return self.throttle_success()

    def throttle_success(self):
        """
        Record successful request and allow it.
        """
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True

    def throttle_failure(self):
        """
        Request is throttled.
        """
        return False

    def wait(self):
        """
        Returns the recommended next request time in seconds.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
            return remaining_duration
        return None

    def get_rate_limit(self, org_id):
        """
        Get the rate limit for an organization.

        Returns:
            int: Rate limit per hour, or -1 for unlimited, or None
        """
        try:
            org = Org.objects.get(id=org_id)
        except (Org.DoesNotExist, ValueError, Exception):
            # If org not found or invalid UUID, use free tier default
            return settings.STRIPE_TIER_FEATURES.get("free", {}).get("api_rate_limit", 100)

        # Check if org has custom api_rate_limit in feature_flags
        if org.feature_flags and "api_rate_limit" in org.feature_flags:
            return org.feature_flags["api_rate_limit"]

        # Fall back to tier defaults
        tier_features = settings.STRIPE_TIER_FEATURES.get(org.license_tier, {})
        rate_limit = tier_features.get("api_rate_limit")

        if rate_limit is None:
            # No tier config, use free tier as default
            return settings.STRIPE_TIER_FEATURES.get("free", {}).get("api_rate_limit", 100)

        return rate_limit

    def get_org_id(self, request):
        """
        Extract org_id from the request.

        Tries multiple sources in order:
        1. token_claims['org_id'] - from JWT
        2. Query parameter 'org_id'
        3. First membership's org_id

        Returns:
            str: Organization ID or None
        """
        # Try token claims first (most reliable)
        if hasattr(request, "token_claims"):
            org_id = request.token_claims.get("org_id")
            if org_id:
                return str(org_id)

        # Try query parameter (common in admin endpoints)
        org_id = request.query_params.get("org_id") if hasattr(request, "query_params") else None
        if org_id:
            return str(org_id)

        # Try user's first membership as fallback
        if hasattr(request, "user") and request.user.is_authenticated:
            membership = request.user.memberships.select_related("org").first()
            if membership:
                return str(membership.org_id)

        return None


def get_org_rate_limit_status(org_id):
    """
    Get the current rate limit status for an organization.

    Args:
        org_id: Organization ID (UUID or string)

    Returns:
        dict: {
            "limit": int or -1 for unlimited,
            "remaining": int or -1 for unlimited,
            "reset_at": timestamp when limit resets,
        }
        Returns None if org not found.
    """
    try:
        org = Org.objects.get(id=org_id)
    except (Org.DoesNotExist, ValueError):
        return None

    # Get rate limit
    if org.feature_flags and "api_rate_limit" in org.feature_flags:
        rate_limit = org.feature_flags["api_rate_limit"]
    else:
        tier_features = settings.STRIPE_TIER_FEATURES.get(org.license_tier, {})
        rate_limit = tier_features.get("api_rate_limit")
        if rate_limit is None:
            rate_limit = settings.STRIPE_TIER_FEATURES.get("free", {}).get("api_rate_limit", 100)

    if rate_limit == -1:
        return {"limit": -1, "remaining": -1, "reset_at": None}

    # Get current usage from cache
    cache = caches["idempotency"]
    cache_key = f"throttle:org:{org_id}"
    history = cache.get(cache_key, [])

    # Count requests in current window
    now = time.time()
    duration = 3600  # 1 hour
    current_count = sum(1 for ts in history if ts > now - duration)

    remaining = max(0, rate_limit - current_count)

    # Calculate reset time
    reset_at = None
    if history:
        oldest_in_window = min(ts for ts in history if ts > now - duration) if current_count > 0 else None
        if oldest_in_window:
            reset_at = oldest_in_window + duration

    return {
        "limit": rate_limit,
        "remaining": remaining,
        "reset_at": reset_at,
    }

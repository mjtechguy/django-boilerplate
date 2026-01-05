"""
API Key creation rate limiting.

Implements per-user throttling for API key creation to prevent abuse
and resource exhaustion attacks. Rate limits are configurable via
the THROTTLE_RATE_API_KEY_CREATE environment variable (default: 5/hour).
"""

import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from rest_framework.throttling import BaseThrottle

User = get_user_model()


class APIKeyCreationThrottle(BaseThrottle):
    """
    Throttle API key creation attempts per user.

    Limits the rate at which a single user can create API keys
    (successful or failed attempts count toward the limit).

    Rate is configured via THROTTLE_RATE_API_KEY_CREATE setting
    in DEFAULT_THROTTLE_RATES (default: 5/hour).
    """

    cache = caches["default"]
    cache_format = "throttle:apikey:create:user:%(user_id)s"
    timer = time.time

    def allow_request(self, request, view):
        """
        Check if the request should be allowed based on user rate limit.

        Returns True if allowed, False if throttled.
        """
        # Only throttle authenticated users
        if not request.user or not request.user.is_authenticated:
            return True

        # Get user ID
        user_id = str(request.user.id)

        # Parse rate limit from settings
        rate = self.get_rate()
        if rate is None:
            # No throttling configured
            return True

        self.num_requests, self.duration = self.parse_rate(rate)

        # Get cache key
        self.key = self.cache_format % {"user_id": user_id}

        # Get current request history
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Remove old entries outside the time window
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        # Check if limit exceeded
        if len(self.history) >= self.num_requests:
            return False

        # Record this request
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True

    def wait(self):
        """
        Returns the recommended next request time in seconds.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
            return max(0, remaining_duration)
        return None

    def get_rate(self):
        """
        Get the throttle rate from Django REST Framework settings.

        Returns the rate string (e.g., "5/hour") or None if not configured.
        """
        if not hasattr(settings, "REST_FRAMEWORK"):
            return None

        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get("api_key_create")

    def parse_rate(self, rate):
        """
        Parse a rate string like "5/hour" into (num_requests, duration).

        Args:
            rate: String in format "num/period" (e.g., "5/hour", "10/day")

        Returns:
            tuple: (num_requests: int, duration: int in seconds)
        """
        num, period = rate.split("/")
        num_requests = int(num)

        duration_map = {
            "s": 1,
            "sec": 1,
            "second": 1,
            "m": 60,
            "min": 60,
            "minute": 60,
            "h": 3600,
            "hour": 3600,
            "d": 86400,
            "day": 86400,
        }

        duration = duration_map.get(period.lower(), 3600)
        return (num_requests, duration)


def get_user_api_key_quota(user):
    """
    Get the maximum number of API keys a user can create based on their org's tier.

    This function determines the max API key quota by:
    1. Getting the user's organization from their first membership
    2. Checking org's feature_flags['max_api_keys'] for custom override
    3. Falling back to tier defaults from STRIPE_TIER_FEATURES
    4. Defaulting to free tier limit (5) if org not found

    Args:
        user: User instance (Django User model)

    Returns:
        int: Maximum API keys allowed (-1 for unlimited, positive int for limit)
    """
    # Validate user
    if not user or not user.is_authenticated:
        # Unauthenticated users get free tier default
        return settings.STRIPE_TIER_FEATURES.get("free", {}).get("max_api_keys", 5)

    # Get user's primary org from first membership
    membership = user.memberships.select_related("org").first()
    if not membership or not membership.org:
        # No org membership, use free tier default
        return settings.STRIPE_TIER_FEATURES.get("free", {}).get("max_api_keys", 5)

    org = membership.org

    # Check if org has custom max_api_keys in feature_flags
    if org.feature_flags and "max_api_keys" in org.feature_flags:
        return org.feature_flags["max_api_keys"]

    # Fall back to tier defaults
    tier_features = settings.STRIPE_TIER_FEATURES.get(org.license_tier, {})
    max_api_keys = tier_features.get("max_api_keys")

    if max_api_keys is None:
        # No tier config, use free tier as default
        return settings.STRIPE_TIER_FEATURES.get("free", {}).get("max_api_keys", 5)

    return max_api_keys

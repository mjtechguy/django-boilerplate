"""
MFA-specific rate limiting for brute force protection.

Implements multi-layer throttling for MFA verification endpoints:
- Per-MFA-token throttle (prevents brute force on a single token)
- Per-user throttle (prevents distributed attacks on one user)
- Per-IP throttle (prevents attacks from one source)
"""

import time

from django.core.cache import caches
from rest_framework.throttling import BaseThrottle

from api.models_mfa import MFAToken


class MFATokenThrottle(BaseThrottle):
    """
    Throttle MFA verification attempts per MFA token.

    Allows 5 failed attempts per token before lockout.
    This prevents brute forcing a single MFA token.

    Only failed attempts are counted - successful verification
    does NOT reset the counter (prevents timing attacks).
    """

    cache = caches["default"]
    cache_format = "throttle:mfa:token:%(token)s"
    timer = time.time
    duration = 900  # 15 minutes
    max_attempts = 5

    def allow_request(self, request, view):
        """Check if request allowed based on per-token limit."""
        mfa_token = request.data.get("mfa_token", "")

        if not mfa_token:
            return True

        self.key = self.cache_format % {"token": mfa_token}
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Remove old entries
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.max_attempts:
            return False

        request._mfa_token_throttle_key = self.key
        return True

    def wait(self):
        """Returns recommended next request time in seconds."""
        if self.history:
            remaining = self.duration - (self.now - self.history[-1])
            return max(0, remaining)
        return None


class MFAUserThrottle(BaseThrottle):
    """
    Throttle MFA verification attempts per user.

    Allows 10 failed attempts per hour per user.
    Prevents distributed attacks targeting one user account.
    """

    cache = caches["default"]
    cache_format = "throttle:mfa:user:%(user_id)s"
    timer = time.time
    duration = 3600  # 1 hour
    max_attempts = 10

    def allow_request(self, request, view):
        """Check if request allowed based on per-user limit."""
        mfa_token = request.data.get("mfa_token", "")

        if not mfa_token:
            return True

        try:
            token_obj = MFAToken.objects.get(token=mfa_token)
            user_id = str(token_obj.user_id)
        except MFAToken.DoesNotExist:
            return True

        self.key = self.cache_format % {"user_id": user_id}
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Remove old entries
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.max_attempts:
            return False

        request._mfa_user_throttle_key = self.key
        return True

    def wait(self):
        """Returns recommended next request time in seconds."""
        if self.history:
            remaining = self.duration - (self.now - self.history[-1])
            return max(0, remaining)
        return None


class MFAIPThrottle(BaseThrottle):
    """
    Throttle MFA verification attempts per IP address.

    Allows 20 failed attempts per hour per IP.
    Prevents attacks from a single source targeting multiple users.
    """

    cache = caches["default"]
    cache_format = "throttle:mfa:ip:%(ip)s"
    timer = time.time
    duration = 3600  # 1 hour
    max_attempts = 20

    def allow_request(self, request, view):
        """Check if request allowed based on per-IP limit."""
        ip = self.get_ident(request)

        if not ip:
            return True

        self.key = self.cache_format % {"ip": ip}
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Remove old entries
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.max_attempts:
            return False

        request._mfa_ip_throttle_key = self.key
        return True

    def wait(self):
        """Returns recommended next request time in seconds."""
        if self.history:
            remaining = self.duration - (self.now - self.history[-1])
            return max(0, remaining)
        return None

    def get_ident(self, request):
        """
        Extract client IP from request.

        Checks X-Forwarded-For first, then REMOTE_ADDR.
        """
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


def increment_mfa_failures(request):
    """
    Increment failure counters for all MFA throttles.

    Called when MFA verification fails.
    Does not increment on success (prevents timing attacks).
    """
    cache = caches["default"]
    now = time.time()

    if hasattr(request, "_mfa_token_throttle_key"):
        key = request._mfa_token_throttle_key
        history = cache.get(key, [])
        history.insert(0, now)
        cache.set(key, history, 900)

    if hasattr(request, "_mfa_user_throttle_key"):
        key = request._mfa_user_throttle_key
        history = cache.get(key, [])
        history.insert(0, now)
        cache.set(key, history, 3600)

    if hasattr(request, "_mfa_ip_throttle_key"):
        key = request._mfa_ip_throttle_key
        history = cache.get(key, [])
        history.insert(0, now)
        cache.set(key, history, 3600)

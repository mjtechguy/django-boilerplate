from .base import *  # noqa: F401,F403

# Test signing key for audit log integrity tests
AUDIT_SIGNING_KEY = "test-signing-key-for-audit-logs"

# Test encryption keys for field encryption tests
FIELD_ENCRYPTION_KEYS = ["test-encryption-key-32-bytes-lon"]  # 32 chars for Fernet

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "idempotency": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

# Use in-memory channel layer for testing (no Redis required)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

DEBUG = True

# Celery test settings
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously in tests
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions in eager mode

# Django-Axes test settings
AXES_ENABLED = False  # Disable axes in tests to avoid lockouts

# Disable rate limiting in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

"""
Production settings with strict security hardening.

These settings enforce HTTPS, secure cookies, HSTS, and other
production-grade security measures.

Usage:
    Set DJANGO_SETTINGS_MODULE=config.settings.production in production.
"""

from .base import *  # noqa: F401,F403

# Force DEBUG off in production
DEBUG = False

# Require SECRET_KEY to be set (fail-fast if not configured)
if SECRET_KEY == "changeme":  # noqa: F405
    raise ValueError("DJANGO_SECRET_KEY must be set in production")

# HTTPS enforcement
SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Trust proxy headers

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True  # Only send over HTTPS
SESSION_COOKIE_HTTPONLY = True  # Not accessible via JavaScript
SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection

CSRF_COOKIE_SECURE = True  # Only send over HTTPS
CSRF_COOKIE_HTTPONLY = True  # Not accessible via JavaScript
CSRF_COOKIE_SAMESITE = "Lax"  # CSRF protection

# Additional security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Tighten CORS in production (should be explicit list of allowed origins)
# CORS_ALLOWED_ORIGINS should be set via environment variable to exact origins

# Tighten CSP in production
# Override any 'unsafe-inline' if your frontend doesn't require it
CSP_STYLE_SRC = ("'self'",)  # Remove 'unsafe-inline' if possible

# Logging - ensure no sensitive data in production logs
AXES_VERBOSE = False  # Don't log verbose info in production

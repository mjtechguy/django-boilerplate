import logging
import os
from pathlib import Path

import structlog
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from config.logging import add_request_context, add_service_info, pii_redactor

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "changeme")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",  # Django Channels ASGI server - must be before django.contrib.staticfiles
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # Required for Wagtail search
    # Wagtail CMS
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    # DRF and other apps
    "rest_framework",
    "rest_framework_api_key",
    "corsheaders",
    "axes",
    "drf_spectacular",
    # Project apps
    "home",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "axes.middleware.AxesMiddleware",
    "config.middleware.AdminHostnameMiddleware",
    "config.middleware.RequestIDMiddleware",
    "api.idempotency.IdempotencyMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Django Channels - WebSocket support with Redis backend
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST", "redis"), int(os.getenv("REDIS_PORT", "6379")))],
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "app"),
        "USER": os.getenv("POSTGRES_USER", "app"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "changeme"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB_CACHE', '0')}",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
    "idempotency": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB_RATELIMIT', '1')}",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
    # Isolated cache for Cerbos authorization decisions (security-sensitive)
    "cerbos": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB_CERBOS', '3')}",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "cerbos",
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.auth.HybridJWTAuthentication",
        "api.auth_access_key.AccessKeyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "api.throttling.OrgRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_RATE_ANON", "100/hour"),
        "user": os.getenv("THROTTLE_RATE_USER", "1000/hour"),
        "org": "1000/hour",  # Default org rate, overridden per-org by license tier
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# OpenAPI / Swagger documentation settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Django Boilerplate API",
    "DESCRIPTION": "Multi-tenant API with Keycloak OIDC auth and Cerbos policy-based authorization",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
}

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
CORS_ALLOW_CREDENTIALS = True

# Content Security Policy (CSP) configuration
# See: https://django-csp.readthedocs.io/
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # unsafe-inline needed for some admin styles
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_FORM_ACTION = ("'self'",)
CSP_BASE_URI = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)

USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
if USE_S3:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
        },
    }
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

# Structlog logging configuration with request context and PII redaction
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
AUDIT_PII_POLICY = os.getenv("AUDIT_PII_POLICY", "mask")  # mask, hash, or drop
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Convert string log level to int for structlog
_LOG_LEVEL_INT = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        add_service_info,
        add_request_context,
        pii_redactor,
        structlog.processors.EventRenamer("message"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_LOG_LEVEL_INT),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
if SENTRY_DSN:
    sentry_init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        environment=SENTRY_ENVIRONMENT,
        send_default_pii=False,  # Don't send PII to Sentry
    )

# Licensing defaults
LICENSE_TIER_DEFAULT = os.getenv("LICENSE_TIER_DEFAULT", "free")
LICENSE_FEATURE_FLAGS_DEFAULT = os.getenv("LICENSE_FEATURE_FLAGS_DEFAULT", "")
# Keycloak settings
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "app")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "api")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", KEYCLOAK_CLIENT_ID)
KEYCLOAK_ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))

# Impersonation settings
IMPERSONATION_ENABLED = os.getenv("IMPERSONATION_ENABLED", "false").lower() == "true"
IMPERSONATION_HEADER = "X-Impersonate-User"

# MFA (Multi-Factor Authentication) Settings
# MFA enforcement is handled by api.mfa module
MFA_REQUIRED = os.getenv("MFA_REQUIRED", "false").lower() == "true"
MFA_REQUIRED_FOR_ADMIN = os.getenv("MFA_REQUIRED_FOR_ADMIN", "true").lower() == "true"
MFA_REQUIRED_ENDPOINTS = ["/api/v1/admin/", "/api/v1/audit/"]
MFA_ACR_VALUES = [
    "urn:keycloak:acr:mfa",
    "urn:keycloak:acr:2fa",
]  # Accepted ACR values for MFA

# Cerbos
CERBOS_URL = os.getenv("CERBOS_URL", "http://cerbos:3592")
CERBOS_DECISION_CACHE_TTL = int(os.getenv("CERBOS_DECISION_CACHE_TTL", "30"))

# Cerbos TLS settings - MUST be true in production
CERBOS_TLS_VERIFY = os.getenv("CERBOS_TLS_VERIFY", "false").lower() == "true"
CERBOS_CA_BUNDLE = os.getenv("CERBOS_CA_BUNDLE", "")

# Celery
CELERY_BROKER_URL = f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:{os.getenv('RABBITMQ_PASSWORD', 'guest')}@{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:{os.getenv('RABBITMQ_PORT', '5672')}//"
CELERY_RESULT_BACKEND = (
    f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/2"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery reliability settings
CELERY_TASK_ACKS_LATE = True  # Acknowledge after task completes (not before)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Reject task if worker dies
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time per worker for fairness

# Retry defaults
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minute initial retry delay
CELERY_TASK_MAX_RETRIES = 3  # Max retries before giving up
CELERY_TASK_RETRY_BACKOFF = True  # Exponential backoff
CELERY_TASK_RETRY_BACKOFF_MAX = 600  # Max 10 minutes between retries
CELERY_TASK_RETRY_JITTER = True  # Add randomness to prevent thundering herd

# Task tracking
CELERY_TASK_TRACK_STARTED = True  # Track when tasks start
CELERY_TASK_TIME_LIMIT = 300  # Hard limit: 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # Soft limit: 4 minutes (raises SoftTimeLimitExceeded)
CELERY_RESULT_EXPIRES = 86400  # Results expire after 24 hours

# Dead letter queue routing
CELERY_TASK_QUEUES = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "dlq": {
        "exchange": "dlq",
        "routing_key": "dlq",
    },
}
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_DEFAULT_EXCHANGE = "default"
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"

# Task deduplication TTL (in Redis)
CELERY_TASK_DEDUP_TTL = int(os.getenv("CELERY_TASK_DEDUP_TTL", "3600"))  # 1 hour default

# Django-Axes (Brute Force Protection)
# Required for axes.middleware.AxesMiddleware
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = int(os.getenv("AXES_FAILURE_LIMIT", "5"))  # Lock after 5 failures
AXES_COOLOFF_TIME = int(os.getenv("AXES_COOLOFF_TIME", "1"))  # Lock for 1 hour (in hours)
AXES_LOCK_OUT_AT_FAILURE = True  # Lock out after failure limit reached
AXES_RESET_ON_SUCCESS = True  # Reset failure count on successful login
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]  # Lock by user and IP combination
AXES_ENABLE_ACCESS_FAILURE_LOG = True  # Log all failed attempts
AXES_VERBOSE = DEBUG  # Verbose logging only in debug mode

# Account Lockout Notification Settings
# Email notifications sent to users when their account is locked due to failed login attempts
LOCKOUT_NOTIFICATION_ENABLED = os.getenv("LOCKOUT_NOTIFICATION_ENABLED", "true").lower() == "true"
LOCKOUT_ADMIN_EMAILS = [
    email.strip()
    for email in os.getenv("LOCKOUT_ADMIN_EMAILS", "").split(",")
    if email.strip()
]
LOCKOUT_MASS_THRESHOLD = int(
    os.getenv("LOCKOUT_MASS_THRESHOLD", "10")
)  # Number of lockouts to trigger admin alert
LOCKOUT_MASS_WINDOW_MINUTES = int(
    os.getenv("LOCKOUT_MASS_WINDOW_MINUTES", "5")
)  # Time window for mass lockout detection

# Security settings (environment-dependent, enforced in production)
# These are set to safe defaults for development, override in production.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Stripe Integration
STRIPE_ENABLED = os.getenv("STRIPE_ENABLED", "false").lower() == "true"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price ID to License Tier Mapping
# Configure these in your environment to map Stripe prices to your license tiers
STRIPE_PRICE_TIER_MAP = {
    os.getenv("STRIPE_PRICE_STARTER", "price_starter"): "starter",
    os.getenv("STRIPE_PRICE_PRO", "price_pro"): "pro",
    os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise"): "enterprise",
}

# Default feature flags per tier
STRIPE_TIER_FEATURES = {
    "free": {
        "max_users": 5,
        "max_teams": 1,
        "api_rate_limit": 100,
        "audit_retention_days": 30,
        "sso_enabled": False,
        "webhooks_enabled": False,
    },
    "starter": {
        "max_users": 25,
        "max_teams": 5,
        "api_rate_limit": 1000,
        "audit_retention_days": 90,
        "sso_enabled": False,
        "webhooks_enabled": True,
    },
    "pro": {
        "max_users": 100,
        "max_teams": 20,
        "api_rate_limit": 10000,
        "audit_retention_days": 365,
        "sso_enabled": True,
        "webhooks_enabled": True,
    },
    "enterprise": {
        "max_users": -1,  # Unlimited
        "max_teams": -1,
        "api_rate_limit": -1,
        "audit_retention_days": -1,  # Unlimited
        "sso_enabled": True,
        "webhooks_enabled": True,
    },
}

# Frontend billing URLs - defined after FRONTEND_URL below
# STRIPE_SUCCESS_URL and STRIPE_CANCEL_URL are set at the end of settings

# Admin hostname separation (production security)
# When set, Django admin is only accessible from this hostname
# In production, set to a separate hostname like "admin.example.com"
ADMIN_HOSTNAME = os.getenv("ADMIN_HOSTNAME", "")

# Email configuration
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# Wagtail CMS settings
WAGTAIL_SITE_NAME = os.getenv("WAGTAIL_SITE_NAME", "Django Boilerplate CMS")
WAGTAILADMIN_BASE_URL = os.getenv("WAGTAILADMIN_BASE_URL", "http://localhost:8000")
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}
# Allow more form fields for complex page models
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Field-Level Encryption
# Generate keys with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEYS = os.getenv("FIELD_ENCRYPTION_KEYS", "").split(",")
FIELD_ENCRYPTION_KEYS = [k.strip() for k in FIELD_ENCRYPTION_KEYS if k.strip()]

# Warn if no encryption keys in non-debug mode
if not DEBUG and not FIELD_ENCRYPTION_KEYS:
    import warnings

    warnings.warn("FIELD_ENCRYPTION_KEYS not set! Sensitive data will not be encrypted.")

# Audit Log Integrity
# Generate key with: python -c "import secrets; print(secrets.token_hex(32))"
AUDIT_SIGNING_KEY = os.getenv("AUDIT_SIGNING_KEY", "")
AUDIT_CHAIN_VERIFICATION_ENABLED = (
    os.getenv("AUDIT_CHAIN_VERIFICATION_ENABLED", "true").lower() == "true"
)

# Warn if no audit signing key in production
if not DEBUG and not AUDIT_SIGNING_KEY:
    import warnings

    warnings.warn(
        "AUDIT_SIGNING_KEY not set! Audit logs will not be signed and tamper-evident features will be disabled."
    )

# Local Authentication Settings
# Enable/disable local username/password authentication
LOCAL_AUTH_ENABLED = os.getenv("LOCAL_AUTH_ENABLED", "true").lower() == "true"
LOCAL_AUTH_ISSUER = os.getenv("LOCAL_AUTH_ISSUER", "local")

# RSA keys for local JWT signing
# Generate with: python -c "from api.local_jwt import generate_key_pair; priv, pub = generate_key_pair(); print('PRIVATE:'); print(priv); print('PUBLIC:'); print(pub)"
LOCAL_AUTH_PRIVATE_KEY = os.getenv("LOCAL_AUTH_PRIVATE_KEY", "")
LOCAL_AUTH_PUBLIC_KEY = os.getenv("LOCAL_AUTH_PUBLIC_KEY", "")

# Token TTL settings
LOCAL_AUTH_ACCESS_TOKEN_TTL = int(os.getenv("LOCAL_AUTH_ACCESS_TOKEN_TTL", "3600"))  # 1 hour
LOCAL_AUTH_REFRESH_TOKEN_TTL = int(os.getenv("LOCAL_AUTH_REFRESH_TOKEN_TTL", "604800"))  # 7 days

# Email verification settings
EMAIL_VERIFICATION_REQUIRED = os.getenv("EMAIL_VERIFICATION_REQUIRED", "true").lower() == "true"
EMAIL_VERIFICATION_TOKEN_TTL = int(os.getenv("EMAIL_VERIFICATION_TOKEN_TTL", "86400"))  # 24 hours

# Password reset settings
PASSWORD_RESET_TOKEN_TTL = int(os.getenv("PASSWORD_RESET_TOKEN_TTL", "3600"))  # 1 hour

# Account lockout settings
LOCAL_AUTH_MAX_FAILED_ATTEMPTS = int(os.getenv("LOCAL_AUTH_MAX_FAILED_ATTEMPTS", "5"))
LOCAL_AUTH_LOCKOUT_DURATION = int(os.getenv("LOCAL_AUTH_LOCKOUT_DURATION", "1800"))  # 30 minutes

# Social Authentication (OAuth)
# Google OAuth - https://console.cloud.google.com/
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# GitHub OAuth - https://github.com/settings/developers
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# Password hashers - Argon2 first for local auth
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Access Key Authentication Settings
# Timestamp tolerance for HMAC signature validation (in seconds)
AKSK_TIMESTAMP_TOLERANCE_SECONDS = int(os.getenv("AKSK_TIMESTAMP_TOLERANCE_SECONDS", "300"))  # 5 minutes

# Frontend URLs for email templates
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Stripe billing redirect URLs (must be after FRONTEND_URL)
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", f"{FRONTEND_URL}/admin/billing/success")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", f"{FRONTEND_URL}/admin/billing")

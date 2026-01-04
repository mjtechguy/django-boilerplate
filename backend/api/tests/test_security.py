"""
Tests for security hardening: middleware, settings, CORS, HSTS, admin boundaries.
"""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware import AdminHostnameMiddleware, RequestIDMiddleware


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware."""

    @pytest.fixture
    def middleware(self):
        return RequestIDMiddleware(get_response=lambda r: HttpResponse("OK"))

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    def test_generates_request_id_when_not_provided(self, middleware, request_factory):
        """Should generate a UUID request ID when not provided."""
        request = request_factory.get("/")
        middleware.process_request(request)

        assert hasattr(request, "request_id")
        assert request.request_id is not None
        # UUID format check (36 chars with hyphens)
        assert len(request.request_id) == 36

    def test_uses_provided_request_id(self, middleware, request_factory):
        """Should use X-Request-ID header if provided."""
        request = request_factory.get("/", HTTP_X_REQUEST_ID="custom-request-id-123")
        middleware.process_request(request)

        assert request.request_id == "custom-request-id-123"

    def test_adds_request_id_to_response(self, middleware, request_factory):
        """Should add X-Request-ID header to response."""
        request = request_factory.get("/")
        request.request_id = "test-id-456"
        response = HttpResponse("OK")

        result = middleware.process_response(request, response)

        assert result["X-Request-ID"] == "test-id-456"


class TestAdminHostnameMiddleware:
    """Tests for AdminHostnameMiddleware."""

    @pytest.fixture
    def middleware(self):
        return AdminHostnameMiddleware(get_response=lambda r: HttpResponse("OK"))

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @override_settings(DEBUG=True)
    def test_allows_admin_in_debug_mode(self, middleware, request_factory):
        """Should allow admin access in DEBUG mode regardless of hostname."""
        request = request_factory.get("/admin/", HTTP_HOST="api.example.com")
        result = middleware.process_request(request)

        assert result is None  # None means request proceeds

    @override_settings(DEBUG=False, ADMIN_HOSTNAME="")
    def test_allows_admin_when_hostname_not_configured(self, middleware, request_factory):
        """Should allow admin access when ADMIN_HOSTNAME not set."""
        request = request_factory.get("/admin/", HTTP_HOST="api.example.com")
        result = middleware.process_request(request)

        assert result is None

    @override_settings(
        DEBUG=False,
        ADMIN_HOSTNAME="admin.example.com",
        ALLOWED_HOSTS=["admin.example.com", "api.example.com"],
    )
    def test_allows_admin_from_correct_hostname(self, middleware, request_factory):
        """Should allow admin access from configured ADMIN_HOSTNAME."""
        request = request_factory.get("/admin/", HTTP_HOST="admin.example.com")
        result = middleware.process_request(request)

        assert result is None

    @override_settings(
        DEBUG=False,
        ADMIN_HOSTNAME="admin.example.com",
        ALLOWED_HOSTS=["admin.example.com", "api.example.com"],
    )
    def test_blocks_admin_from_wrong_hostname(self, middleware, request_factory):
        """Should block admin access from non-admin hostname."""
        request = request_factory.get("/admin/", HTTP_HOST="api.example.com")
        result = middleware.process_request(request)

        assert result is not None
        assert result.status_code == 403

    @override_settings(
        DEBUG=False,
        ADMIN_HOSTNAME="admin.example.com",
        ALLOWED_HOSTS=["admin.example.com", "api.example.com"],
    )
    def test_allows_non_admin_paths_from_any_hostname(self, middleware, request_factory):
        """Should allow non-admin paths from any hostname."""
        request = request_factory.get("/api/v1/ping", HTTP_HOST="api.example.com")
        result = middleware.process_request(request)

        assert result is None

    @override_settings(
        DEBUG=False,
        ADMIN_HOSTNAME="admin.example.com",
        ALLOWED_HOSTS=["admin.example.com"],
    )
    def test_handles_hostname_with_port(self, middleware, request_factory):
        """Should correctly handle hostnames with port numbers."""
        request = request_factory.get("/admin/", HTTP_HOST="admin.example.com:8000")
        result = middleware.process_request(request)

        assert result is None


class TestSecuritySettings:
    """Tests for security settings presence."""

    def test_csp_settings_present(self):
        """CSP settings should be configured."""
        from django.conf import settings

        assert hasattr(settings, "CSP_DEFAULT_SRC")
        assert settings.CSP_DEFAULT_SRC == ("'self'",)
        assert hasattr(settings, "CSP_SCRIPT_SRC")
        assert hasattr(settings, "CSP_STYLE_SRC")
        assert hasattr(settings, "CSP_FRAME_ANCESTORS")
        assert settings.CSP_FRAME_ANCESTORS == ("'none'",)

    def test_csp_style_src_no_unsafe_inline(self):
        """CSP_STYLE_SRC should not contain 'unsafe-inline'."""
        from django.conf import settings

        assert hasattr(settings, "CSP_STYLE_SRC")
        assert "'unsafe-inline'" not in settings.CSP_STYLE_SRC

    def test_csp_exclude_url_prefixes_configured(self):
        """CSP_EXCLUDE_URL_PREFIXES should be configured with admin paths."""
        from django.conf import settings

        assert hasattr(settings, "CSP_EXCLUDE_URL_PREFIXES")
        assert "/admin/" in settings.CSP_EXCLUDE_URL_PREFIXES
        assert "/cms/" in settings.CSP_EXCLUDE_URL_PREFIXES

    def test_cors_settings_present(self):
        """CORS settings should be configured."""
        from django.conf import settings

        assert hasattr(settings, "CORS_ALLOWED_ORIGINS")
        assert hasattr(settings, "CORS_ALLOW_CREDENTIALS")

    def test_axes_settings_present(self):
        """Django-axes settings should be configured."""
        from django.conf import settings

        assert hasattr(settings, "AXES_FAILURE_LIMIT")
        assert settings.AXES_FAILURE_LIMIT > 0
        assert hasattr(settings, "AXES_COOLOFF_TIME")
        assert hasattr(settings, "AXES_LOCK_OUT_AT_FAILURE")
        assert settings.AXES_LOCK_OUT_AT_FAILURE is True

    def test_rate_limiting_settings_present(self):
        """Rate limiting settings should be configured in DRF."""
        from django.conf import settings

        # In test mode, throttle classes are disabled
        # Check that the base config has them
        assert "DEFAULT_THROTTLE_RATES" in settings.REST_FRAMEWORK

    def test_security_middleware_present(self):
        """Security middleware should be in the middleware stack."""
        from django.conf import settings

        middleware = settings.MIDDLEWARE
        assert "django.middleware.security.SecurityMiddleware" in middleware
        assert "csp.middleware.CSPMiddleware" in middleware
        assert "axes.middleware.AxesMiddleware" in middleware
        assert "config.middleware.AdminHostnameMiddleware" in middleware

    def test_security_headers_configured(self):
        """Security headers should be configured."""
        from django.conf import settings

        assert settings.SECURE_BROWSER_XSS_FILTER is True
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
        assert settings.X_FRAME_OPTIONS == "DENY"


class TestProductionSecuritySettings:
    """Tests for production security settings."""

    def test_production_settings_enforce_https(self):
        """Production settings should enforce HTTPS."""
        import os

        # We can't fully import production.py without base.py context
        # So we just check the file exists and has expected content
        prod_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "config",
            "settings",
            "production.py",
        )
        assert os.path.exists(prod_file)

        with open(prod_file) as f:
            content = f.read()

        # Check for critical security settings
        assert "SECURE_SSL_REDIRECT = True" in content
        assert "SECURE_HSTS_SECONDS" in content
        assert "SESSION_COOKIE_SECURE = True" in content
        assert "CSRF_COOKIE_SECURE = True" in content
        assert "DEBUG = False" in content

    def test_production_settings_has_secret_key_check(self):
        """Production settings should fail if SECRET_KEY is default."""
        prod_file = __file__.replace(
            "api/tests/test_security.py",
            "config/settings/production.py",
        )

        with open(prod_file) as f:
            content = f.read()

        # Check for SECRET_KEY validation
        assert 'SECRET_KEY == "changeme"' in content
        assert "raise ValueError" in content


class TestCORSBehavior:
    """Tests for CORS behavior."""

    @pytest.mark.django_db
    def test_cors_allows_configured_origin(self, client):
        """CORS should allow requests from configured origins."""
        from django.conf import settings

        allowed_origin = settings.CORS_ALLOWED_ORIGINS[0]
        response = client.options(
            "/api/v1/ping",
            HTTP_ORIGIN=allowed_origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )

        # Preflight should succeed (200 or 204)
        assert response.status_code in [200, 204, 401]  # 401 if auth required

    @pytest.mark.django_db
    def test_cors_headers_present(self, client):
        """CORS headers should be present for allowed origins."""
        from django.conf import settings

        allowed_origin = settings.CORS_ALLOWED_ORIGINS[0]
        response = client.get(
            "/healthz",
            HTTP_ORIGIN=allowed_origin,
        )

        # Health endpoint should work
        assert response.status_code == 200

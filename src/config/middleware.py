import time
import uuid

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from config.observability import clear_request_context, metrics, set_request_context


class RequestIDMiddleware(MiddlewareMixin):
    """Attach a request_id to each request/response cycle and bind logging context."""

    def process_request(self, request):
        request_id = request.headers.get("X-Request-ID")
        trace_id = request.headers.get("X-Trace-ID", "")
        if not request_id:
            request_id = str(uuid.uuid4())
        request.request_id = request_id
        request._start_time = time.perf_counter()

        # Extract actor and org_id from token claims if available
        claims = getattr(request, "token_claims", {})
        actor = claims.get("sub", "")
        org_id = claims.get("org_id", "")

        # Set request context for structured logging
        set_request_context(
            request_id=request_id,
            trace_id=trace_id or request_id,
            actor=actor,
            org_id=org_id,
            path=request.path,
            method=request.method,
        )

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id

        # Record request duration metric
        start_time = getattr(request, "_start_time", None)
        if start_time:
            duration = time.perf_counter() - start_time
            metrics.observe(
                "http_request_duration_seconds",
                duration,
                labels={
                    "method": request.method,
                    "path": request.path,
                    "status": str(response.status_code),
                },
            )
            metrics.inc(
                "http_requests_total",
                labels={
                    "method": request.method,
                    "status": str(response.status_code),
                },
            )

        # Clear request context
        clear_request_context()

        return response


class AdminHostnameMiddleware(MiddlewareMixin):
    """
    Restrict Django admin access to a specific hostname.

    In production, the Django admin should only be accessible via a separate
    hostname (e.g., admin.example.com) to prevent accidental exposure on the
    main API hostname.

    Configuration:
        ADMIN_HOSTNAME: The hostname where admin is allowed (e.g., "admin.example.com")
        If not set or DEBUG=True, admin is accessible on all hosts.

    Usage:
        Add 'config.middleware.AdminHostnameMiddleware' to MIDDLEWARE after
        SessionMiddleware and AuthenticationMiddleware.

    Production setup:
        1. Set ADMIN_HOSTNAME=admin.example.com in environment
        2. Configure reverse proxy/ingress to route admin.example.com to this service
        3. Ensure admin.example.com is in ALLOWED_HOSTS
    """

    def process_request(self, request):
        # Skip in debug mode
        if settings.DEBUG:
            return None

        # Check if admin hostname restriction is configured
        admin_hostname = getattr(settings, "ADMIN_HOSTNAME", None)
        if not admin_hostname:
            return None

        # Only restrict admin paths
        if not request.path.startswith("/admin"):
            return None

        # Allow if hostname matches
        request_host = request.get_host().split(":")[0]  # Remove port if present
        if request_host == admin_hostname:
            return None

        # Deny access to admin from non-admin hostname
        return HttpResponseForbidden(
            b"Admin access is only available via the admin hostname.",
            content_type="text/plain",
        )

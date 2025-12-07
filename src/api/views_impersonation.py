"""
REST API views for impersonation log access.

Provides read-only access to impersonation logs with filtering capabilities.
Only accessible to platform_admin users.
"""

import structlog
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.auth import KeycloakJWTAuthentication
from api.models import ImpersonationLog
from api.permissions import IsPlatformAdmin
from api.serializers_impersonation import ImpersonationLogSerializer

logger = structlog.get_logger(__name__)


class ImpersonationLogListView(APIView):
    """
    List impersonation logs - platform_admin only.

    Only platform administrators can view impersonation logs.

    GET /api/v1/admin/impersonation/logs

    Query parameters:
    - admin_id: Filter by admin user ID
    - target_user_id: Filter by target user ID
    - org_id: Filter by organization ID
    - action: Filter by action (start, end, etc.)
    - start_date: Filter by start date (ISO 8601 format)
    - end_date: Filter by end date (ISO 8601 format)
    - limit: Number of results to return (default: 50, max: 1000)
    - offset: Number of results to skip (default: 0)

    Example:
        GET /api/v1/admin/impersonation/logs?admin_id=user-123&limit=100
    """

    authentication_classes = [KeycloakJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """List impersonation logs with filtering."""
        # Log access to impersonation logs
        claims = getattr(request, "token_claims", {})
        logger.info(
            "impersonation_log_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )

        # Start with all impersonation logs
        queryset = ImpersonationLog.objects.all()

        # Apply filters
        admin_id = request.query_params.get("admin_id")
        if admin_id:
            queryset = queryset.filter(admin_id=admin_id)

        target_user_id = request.query_params.get("target_user_id")
        if target_user_id:
            queryset = queryset.filter(target_user_id=target_user_id)

        org_id = request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(org_id=org_id)

        action = request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        # Date range filters
        start_date_str = request.query_params.get("start_date")
        if start_date_str:
            start_date = parse_datetime(start_date_str)
            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)

        end_date_str = request.query_params.get("end_date")
        if end_date_str:
            end_date = parse_datetime(end_date_str)
            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)

        # Pagination
        limit = int(request.query_params.get("limit", 50))
        limit = min(limit, 1000)  # Max 1000 results
        offset = int(request.query_params.get("offset", 0))

        # Get total count before pagination
        total_count = queryset.count()

        # Apply pagination
        queryset = queryset[offset : offset + limit]

        # Serialize and return
        serializer = ImpersonationLogSerializer(queryset, many=True)

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )

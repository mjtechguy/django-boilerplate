"""
REST API views for organization admin management.

Provides CRUD operations for organizations, accessible only to platform_admin users.
"""

import structlog
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Org
from api.permissions import IsPlatformAdmin
from api.serializers_admin import (
    OrgCreateSerializer,
    OrgListSerializer,
    OrgSerializer,
    OrgUpdateSerializer,
)

logger = structlog.get_logger(__name__)


class AdminOrgListCreateView(APIView):
    """
    List and create organizations - platform_admin only.

    GET /api/v1/admin/orgs
        Query parameters:
        - search: Search by name (case-insensitive contains)
        - status: Filter by status (active, inactive)
        - license_tier: Filter by license tier
        - limit: Number of results to return (default: 50, max: 1000)
        - offset: Number of results to skip (default: 0)

    POST /api/v1/admin/orgs
        Create a new organization.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """List all organizations with filtering and pagination."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_org_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )

        # Build queryset with annotations for counts
        queryset = Org.objects.annotate(
            _teams_count=Count("teams", distinct=True),
            _members_count=Count("memberships__user_id", distinct=True),
        )

        # Apply filters
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        license_tier = request.query_params.get("license_tier")
        if license_tier:
            queryset = queryset.filter(license_tier=license_tier)

        # Order by created_at descending
        queryset = queryset.order_by("-created_at")

        # Pagination
        limit = min(int(request.query_params.get("limit", 50)), 1000)
        offset = int(request.query_params.get("offset", 0))

        total_count = queryset.count()
        results = queryset[offset : offset + limit]

        serializer = OrgListSerializer(results, many=True)

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )

    def post(self, request: Request) -> Response:
        """Create a new organization."""
        claims = getattr(request, "token_claims", {})

        serializer = OrgCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        org = serializer.save()

        logger.info(
            "admin_org_created",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org.id),
            org_name=org.name,
            license_tier=org.license_tier,
        )

        return Response(OrgSerializer(org).data, status=status.HTTP_201_CREATED)


class AdminOrgDetailView(APIView):
    """
    Get, update, or delete an organization - platform_admin only.

    GET /api/v1/admin/orgs/{org_id}
        Get organization details.

    PUT /api/v1/admin/orgs/{org_id}
        Update organization.

    DELETE /api/v1/admin/orgs/{org_id}
        Deactivate organization (soft delete via status change).
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get_object(self, org_id) -> Org | None:
        """Get org by ID or return None."""
        try:
            return Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return None

    def get(self, request: Request, org_id) -> Response:
        """Get organization details."""
        org = self.get_object(org_id)
        if not org:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_org_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            org_id=str(org_id),
        )

        serializer = OrgSerializer(org)
        return Response(serializer.data)

    def put(self, request: Request, org_id) -> Response:
        """Update organization."""
        org = self.get_object(org_id)
        if not org:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        old_values = {
            "name": org.name,
            "status": org.status,
            "license_tier": org.license_tier,
            "feature_flags": org.feature_flags,
        }

        serializer = OrgUpdateSerializer(org, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        org = serializer.save()

        # Log changes
        changes = {}
        for field, old_val in old_values.items():
            new_val = getattr(org, field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}

        logger.info(
            "admin_org_updated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org.id),
            org_name=org.name,
            changes=changes,
        )

        return Response(OrgSerializer(org).data)

    def delete(self, request: Request, org_id) -> Response:
        """Deactivate organization (soft delete)."""
        org = self.get_object(org_id)
        if not org:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})

        # Soft delete by setting status to inactive
        old_status = org.status
        org.status = Org.Status.INACTIVE
        org.save(update_fields=["status", "updated_at"])

        logger.info(
            "admin_org_deactivated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org.id),
            org_name=org.name,
            old_status=old_status,
        )

        return Response(
            {"message": "Organization deactivated", "org_id": str(org.id)},
            status=status.HTTP_200_OK,
        )

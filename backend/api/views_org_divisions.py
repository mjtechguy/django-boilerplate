"""
REST API views for org-scoped division management.

Allows org admins to manage divisions within their organization.
"""

import structlog
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import Division, Team
from api.permissions_org import IsOrgAdminForOrg, IsDivisionAdminForDivision
from api.serializers_admin import (
    DivisionCreateSerializer,
    DivisionListSerializer,
    DivisionSerializer,
    DivisionUpdateSerializer,
    TeamListSerializer,
)

logger = structlog.get_logger(__name__)


class OrgDivisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for org-scoped division management - org_admin only.

    Provides CRUD operations for divisions within a specific organization.

    Endpoints:
    - GET /api/v1/orgs/{org_id}/divisions - List divisions in org
    - POST /api/v1/orgs/{org_id}/divisions - Create a new division
    - GET /api/v1/orgs/{org_id}/divisions/{id} - Get division details
    - PUT /api/v1/orgs/{org_id}/divisions/{id} - Update division
    - PATCH /api/v1/orgs/{org_id}/divisions/{id} - Partially update division
    - DELETE /api/v1/orgs/{org_id}/divisions/{id} - Delete division
    - GET /api/v1/orgs/{org_id}/divisions/{id}/teams - Get division teams
    """

    permission_classes = [IsAuthenticated, IsOrgAdminForOrg]
    serializer_class = DivisionSerializer

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return DivisionListSerializer
        elif self.action == "create":
            return DivisionCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return DivisionUpdateSerializer
        return DivisionSerializer

    def get_queryset(self):
        """Get queryset filtered by org_id from URL."""
        org_id = self.kwargs.get("org_id")
        queryset = Division.objects.filter(org_id=org_id).select_related("org").annotate(
            _teams_count=Count("teams", distinct=True),
            _members_count=Count("memberships", distinct=True),
        )

        # Apply optional filters from query params
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        billing_mode = self.request.query_params.get("billing_mode")
        if billing_mode:
            queryset = queryset.filter(billing_mode=billing_mode)

        return queryset.order_by("-created_at")

    def list(self, request: Request, org_id=None) -> Response:
        """List all divisions in the organization."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "org_division_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org_id),
            query_params=dict(request.query_params),
        )
        return super().list(request)

    def create(self, request: Request, org_id=None) -> Response:
        """Create a new division in the organization."""
        claims = getattr(request, "token_claims", {})

        # Ensure org_id in request data matches URL
        data = request.data.copy()
        data["org"] = str(org_id)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        division = serializer.save()

        logger.info(
            "org_division_created",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            division_id=str(division.id),
            division_name=division.name,
            org_id=str(division.org_id),
            billing_mode=division.billing_mode,
        )

        return Response(
            DivisionSerializer(division).data,
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, org_id=None, pk=None) -> Response:
        """Get division details."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "org_division_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            org_id=str(org_id),
            division_id=str(pk),
        )
        return super().retrieve(request, pk=pk)

    def update(self, request: Request, org_id=None, pk=None) -> Response:
        """Update division."""
        claims = getattr(request, "token_claims", {})
        division = self.get_object()

        old_values = {
            "name": division.name,
            "billing_mode": division.billing_mode,
            "license_tier": division.license_tier,
        }

        response = super().update(request, pk=pk)

        if response.status_code == status.HTTP_200_OK:
            division.refresh_from_db()
            changes = {}
            if old_values["name"] != division.name:
                changes["name"] = {"old": old_values["name"], "new": division.name}
            if old_values["billing_mode"] != division.billing_mode:
                changes["billing_mode"] = {"old": old_values["billing_mode"], "new": division.billing_mode}
            if old_values["license_tier"] != division.license_tier:
                changes["license_tier"] = {"old": old_values["license_tier"], "new": division.license_tier}

            logger.info(
                "org_division_updated",
                actor_id=claims.get("sub", "unknown"),
                actor_email=claims.get("email"),
                division_id=str(division.id),
                division_name=division.name,
                org_id=str(division.org_id),
                changes=changes,
            )

        return response

    def destroy(self, request: Request, org_id=None, pk=None) -> Response:
        """Delete division."""
        claims = getattr(request, "token_claims", {})
        division = self.get_object()
        division_id = str(division.id)
        division_name = division.name

        response = super().destroy(request, pk=pk)

        if response.status_code == status.HTTP_204_NO_CONTENT:
            logger.info(
                "org_division_deleted",
                actor_id=claims.get("sub", "unknown"),
                actor_email=claims.get("email"),
                division_id=division_id,
                division_name=division_name,
                org_id=str(org_id),
            )

        return response

    @action(detail=True, methods=["get"])
    def teams(self, request: Request, org_id=None, pk=None) -> Response:
        """Get all teams in this division."""
        division = self.get_object()
        claims = getattr(request, "token_claims", {})

        logger.info(
            "org_division_teams_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org_id),
            division_id=str(pk),
        )

        # Build queryset with annotations
        queryset = Team.objects.filter(division_id=pk).select_related(
            "org", "division"
        ).annotate(
            _members_count=Count("memberships", distinct=True),
        ).order_by("-created_at")

        # Pagination
        limit = min(int(request.query_params.get("limit", 50)), 1000)
        offset = int(request.query_params.get("offset", 0))

        total_count = queryset.count()
        results = queryset[offset : offset + limit]

        serializer = TeamListSerializer(results, many=True)

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )

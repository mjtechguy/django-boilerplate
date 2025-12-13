"""
REST API views for division admin management.

Provides CRUD operations for divisions, accessible only to platform_admin users.
"""

import structlog
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import Division, Team
from api.permissions import IsPlatformAdmin
from api.serializers_admin import (
    DivisionCreateSerializer,
    DivisionListSerializer,
    DivisionSerializer,
    DivisionUpdateSerializer,
)

logger = structlog.get_logger(__name__)


class AdminDivisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin division management - platform_admin only.

    Provides CRUD operations for divisions across all organizations.

    Endpoints:
    - GET /api/v1/admin/divisions - List all divisions
    - POST /api/v1/admin/divisions - Create a new division
    - GET /api/v1/admin/divisions/{id} - Get division details
    - PUT /api/v1/admin/divisions/{id} - Update division
    - PATCH /api/v1/admin/divisions/{id} - Partially update division
    - DELETE /api/v1/admin/divisions/{id} - Delete division
    - GET /api/v1/admin/divisions/{id}/teams - Get division teams
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    queryset = Division.objects.select_related("org").all()

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
        """Get queryset with optional filtering and annotations."""
        queryset = Division.objects.select_related("org").annotate(
            _teams_count=Count("teams", distinct=True),
            _members_count=Count("memberships", distinct=True),
        )

        # Apply filters from query params
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        org_id = self.request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(org_id=org_id)

        billing_mode = self.request.query_params.get("billing_mode")
        if billing_mode:
            queryset = queryset.filter(billing_mode=billing_mode)

        return queryset.order_by("-created_at")

    def list(self, request: Request, *args, **kwargs) -> Response:
        """List all divisions with filtering and pagination."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_division_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )
        return super().list(request, *args, **kwargs)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new division."""
        claims = getattr(request, "token_claims", {})
        response = super().create(request, *args, **kwargs)

        if response.status_code == status.HTTP_201_CREATED:
            division_data = response.data
            logger.info(
                "admin_division_created",
                actor_id=claims.get("sub", "unknown"),
                actor_email=claims.get("email"),
                division_id=division_data.get("id"),
                division_name=division_data.get("name"),
                org_id=division_data.get("org"),
                billing_mode=division_data.get("billing_mode"),
            )

        return response

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Get division details."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_division_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            pk=kwargs.get("pk"),
        )
        return super().retrieve(request, *args, **kwargs)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update division."""
        claims = getattr(request, "token_claims", {})
        division = self.get_object()
        old_values = {
            "name": division.name,
            "billing_mode": division.billing_mode,
            "license_tier": division.license_tier,
        }

        response = super().update(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            # Log changes
            division.refresh_from_db()
            changes = {}
            if old_values["name"] != division.name:
                changes["name"] = {"old": old_values["name"], "new": division.name}
            if old_values["billing_mode"] != division.billing_mode:
                changes["billing_mode"] = {"old": old_values["billing_mode"], "new": division.billing_mode}
            if old_values["license_tier"] != division.license_tier:
                changes["license_tier"] = {"old": old_values["license_tier"], "new": division.license_tier}

            logger.info(
                "admin_division_updated",
                actor_id=claims.get("sub", "unknown"),
                actor_email=claims.get("email"),
                division_id=str(division.id),
                division_name=division.name,
                org_id=str(division.org_id),
                changes=changes,
            )

        return response

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete division."""
        claims = getattr(request, "token_claims", {})
        division = self.get_object()
        division_id = str(division.id)
        division_name = division.name
        org_id = str(division.org_id)

        response = super().destroy(request, *args, **kwargs)

        if response.status_code == status.HTTP_204_NO_CONTENT:
            logger.info(
                "admin_division_deleted",
                actor_id=claims.get("sub", "unknown"),
                actor_email=claims.get("email"),
                division_id=division_id,
                division_name=division_name,
                org_id=org_id,
            )

        return response

    @action(detail=True, methods=["get"])
    def teams(self, request: Request, pk=None) -> Response:
        """Get all teams in this division."""
        division = self.get_object()
        claims = getattr(request, "token_claims", {})

        logger.info(
            "admin_division_teams_accessed",
            actor_id=claims.get("sub", "unknown"),
            division_id=str(pk),
        )

        teams = Team.objects.filter(division=division).select_related("org")

        teams_data = []
        for team in teams:
            teams_data.append({
                "id": str(team.id),
                "name": team.name,
                "org_id": str(team.org_id),
                "division_id": str(team.division_id) if team.division_id else None,
                "created_at": team.created_at.isoformat(),
            })

        return Response({
            "division_id": str(pk),
            "division_name": division.name,
            "count": len(teams_data),
            "teams": teams_data,
        })

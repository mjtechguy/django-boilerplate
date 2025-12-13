"""
REST API views for org-scoped team management.

Allows org admins to manage teams within their organization.
"""

import structlog
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Membership, Team
from api.permissions_org import IsOrgAdminForOrg
from api.serializers_admin import (
    TeamCreateSerializer,
    TeamListSerializer,
    TeamSerializer,
    TeamUpdateSerializer,
)

logger = structlog.get_logger(__name__)


class OrgTeamListCreateView(APIView):
    """
    List and create teams for a specific organization - org_admin only.

    GET /api/v1/orgs/{org_id}/teams
        Query parameters:
        - search: Search by name (case-insensitive contains)
        - division_id: Filter teams by division
        - limit: Number of results to return (default: 50, max: 1000)
        - offset: Number of results to skip (default: 0)

    POST /api/v1/orgs/{org_id}/teams
        Create a new team in this organization.
    """

    permission_classes = [IsAuthenticated, IsOrgAdminForOrg]

    def get(self, request: Request, org_id) -> Response:
        """List all teams in the organization."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "org_team_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org_id),
            query_params=dict(request.query_params),
        )

        # Build queryset with annotations for counts
        queryset = Team.objects.filter(org_id=org_id).select_related("org", "division").annotate(
            _members_count=Count("memberships", distinct=True),
        )

        # Apply filters
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        division_id = request.query_params.get("division_id")
        if division_id:
            queryset = queryset.filter(division_id=division_id)

        # Order by created_at descending
        queryset = queryset.order_by("-created_at")

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

    def post(self, request: Request, org_id) -> Response:
        """Create a new team in the organization."""
        claims = getattr(request, "token_claims", {})

        # Ensure org_id in request data matches URL
        data = request.data.copy()
        data["org"] = str(org_id)

        serializer = TeamCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        team = serializer.save()

        logger.info(
            "org_team_created",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            team_id=str(team.id),
            team_name=team.name,
            org_id=str(team.org_id),
        )

        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class OrgTeamDetailView(APIView):
    """
    Get, update, or delete a team - org_admin only.

    GET /api/v1/orgs/{org_id}/teams/{team_id}
        Get team details.

    PUT /api/v1/orgs/{org_id}/teams/{team_id}
        Update team.

    DELETE /api/v1/orgs/{org_id}/teams/{team_id}
        Delete team.
    """

    permission_classes = [IsAuthenticated, IsOrgAdminForOrg]

    def get_object(self, org_id, team_id) -> Team | None:
        """Get team by ID within the org or return None."""
        try:
            return Team.objects.select_related("org", "division").get(id=team_id, org_id=org_id)
        except Team.DoesNotExist:
            return None

    def get(self, request: Request, org_id, team_id) -> Response:
        """Get team details."""
        team = self.get_object(org_id, team_id)
        if not team:
            return Response(
                {"error": "Team not found in this organization"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "org_team_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            org_id=str(org_id),
            team_id=str(team_id),
        )

        serializer = TeamSerializer(team)
        return Response(serializer.data)

    def put(self, request: Request, org_id, team_id) -> Response:
        """Update team."""
        team = self.get_object(org_id, team_id)
        if not team:
            return Response(
                {"error": "Team not found in this organization"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        old_name = team.name

        serializer = TeamUpdateSerializer(team, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        team = serializer.save()

        # Log changes
        changes = {}
        if old_name != team.name:
            changes["name"] = {"old": old_name, "new": team.name}

        logger.info(
            "org_team_updated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            team_id=str(team.id),
            team_name=team.name,
            org_id=str(team.org_id),
            changes=changes,
        )

        return Response(TeamSerializer(team).data)

    def delete(self, request: Request, org_id, team_id) -> Response:
        """Delete team."""
        team = self.get_object(org_id, team_id)
        if not team:
            return Response(
                {"error": "Team not found in this organization"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        team_name = team.name

        # Hard delete the team
        team.delete()

        logger.info(
            "org_team_deleted",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            team_id=str(team_id),
            team_name=team_name,
            org_id=str(org_id),
        )

        return Response(
            {"message": "Team deleted", "team_id": str(team_id)},
            status=status.HTTP_200_OK,
        )

"""
REST API views for team admin management.

Provides CRUD operations for teams, accessible only to platform_admin users.
"""

import structlog
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Membership, Team
from api.permissions import IsPlatformAdmin
from api.serializers_admin import (
    TeamCreateSerializer,
    TeamListSerializer,
    TeamSerializer,
    TeamUpdateSerializer,
)

logger = structlog.get_logger(__name__)


class AdminTeamListCreateView(APIView):
    """
    List and create teams - platform_admin only.

    GET /api/v1/admin/teams
        Query parameters:
        - search: Search by name (case-insensitive contains)
        - org_id: Filter by organization ID
        - limit: Number of results to return (default: 50, max: 1000)
        - offset: Number of results to skip (default: 0)

    POST /api/v1/admin/teams
        Create a new team.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """List all teams with filtering and pagination."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_team_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )

        # Build queryset with annotations for counts
        queryset = Team.objects.select_related("org").annotate(
            _members_count=Count("memberships", distinct=True),
        )

        # Apply filters
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        org_id = request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(org_id=org_id)

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

    def post(self, request: Request) -> Response:
        """Create a new team."""
        claims = getattr(request, "token_claims", {})

        serializer = TeamCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        team = serializer.save()

        logger.info(
            "admin_team_created",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            team_id=str(team.id),
            team_name=team.name,
            org_id=str(team.org_id),
        )

        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class AdminTeamDetailView(APIView):
    """
    Get, update, or delete a team - platform_admin only.

    GET /api/v1/admin/teams/{team_id}
        Get team details.

    PUT /api/v1/admin/teams/{team_id}
        Update team.

    DELETE /api/v1/admin/teams/{team_id}
        Delete team.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get_object(self, team_id) -> Team | None:
        """Get team by ID or return None."""
        try:
            return Team.objects.select_related("org").get(id=team_id)
        except Team.DoesNotExist:
            return None

    def get(self, request: Request, team_id) -> Response:
        """Get team details."""
        team = self.get_object(team_id)
        if not team:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_team_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            team_id=str(team_id),
        )

        serializer = TeamSerializer(team)
        return Response(serializer.data)

    def put(self, request: Request, team_id) -> Response:
        """Update team."""
        team = self.get_object(team_id)
        if not team:
            return Response(
                {"error": "Team not found"},
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
            "admin_team_updated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            team_id=str(team.id),
            team_name=team.name,
            org_id=str(team.org_id),
            changes=changes,
        )

        return Response(TeamSerializer(team).data)

    def delete(self, request: Request, team_id) -> Response:
        """Delete team."""
        team = self.get_object(team_id)
        if not team:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        team_name = team.name
        org_id = str(team.org_id)

        # Hard delete the team
        team.delete()

        logger.info(
            "admin_team_deleted",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            team_id=str(team_id),
            team_name=team_name,
            org_id=org_id,
        )

        return Response(
            {"message": "Team deleted", "team_id": str(team_id)},
            status=status.HTTP_200_OK,
        )


class AdminTeamMembersView(APIView):
    """
    List team members - platform_admin only.

    GET /api/v1/admin/teams/{team_id}/members
        List all members of a team.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request, team_id) -> Response:
        """List team members."""
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_team_members_accessed",
            actor_id=claims.get("sub", "unknown"),
            team_id=str(team_id),
        )

        # Get memberships with user info
        memberships = Membership.objects.filter(team=team).select_related("user")

        # Build response with user details
        members = []
        for membership in memberships:
            user = membership.user
            members.append(
                {
                    "membership_id": str(membership.id),
                    "user_id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "team_roles": membership.team_roles,
                    "joined_at": membership.created_at.isoformat(),
                }
            )

        return Response(
            {
                "team_id": str(team_id),
                "team_name": team.name,
                "count": len(members),
                "members": members,
            }
        )

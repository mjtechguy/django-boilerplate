"""
REST API views for org-scoped member management.

Allows org admins to manage members (users with memberships) within their organization.
"""

import structlog
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Membership, Org
from api.permissions_org import IsOrgAdminForOrg
from api.serializers_admin import (
    MembershipCreateSerializer,
    MembershipListSerializer,
    MembershipSerializer,
)

User = get_user_model()
logger = structlog.get_logger(__name__)


class OrgMemberListCreateView(APIView):
    """
    List and add members to an organization - org_admin only.

    GET /api/v1/orgs/{org_id}/members
        List all members (users with memberships) in the organization.
        Query parameters:
        - search: Search by email, first_name, last_name
        - team_id: Filter by team membership
        - limit: Number of results to return (default: 50, max: 1000)
        - offset: Number of results to skip (default: 0)

    POST /api/v1/orgs/{org_id}/members
        Add a member to the organization (create membership).
        Body: {
            "user_id": "user-uuid",
            "team_id": "team-uuid" (optional),
            "org_roles": ["user", "org_admin"] (optional),
            "team_roles": ["member", "lead"] (optional)
        }
    """

    permission_classes = [IsAuthenticated, IsOrgAdminForOrg]

    def get(self, request: Request, org_id) -> Response:
        """List all members in the organization."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "org_member_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=str(org_id),
            query_params=dict(request.query_params),
        )

        # Verify org exists
        try:
            Org.objects.get(id=org_id)
        except Org.DoesNotExist:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Build queryset for memberships in this org
        queryset = Membership.objects.filter(org_id=org_id).select_related("user", "org", "team")

        # Apply filters
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        team_id = request.query_params.get("team_id")
        if team_id:
            queryset = queryset.filter(team_id=team_id)

        # Order by created_at descending
        queryset = queryset.order_by("-created_at")

        # Pagination
        limit = min(int(request.query_params.get("limit", 50)), 1000)
        offset = int(request.query_params.get("offset", 0))

        total_count = queryset.count()
        results = queryset[offset : offset + limit]

        serializer = MembershipListSerializer(results, many=True)

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )

    def post(self, request: Request, org_id) -> Response:
        """Add a member to the organization."""
        claims = getattr(request, "token_claims", {})

        # Ensure org_id in request data matches URL
        data = request.data.copy()
        data["org"] = str(org_id)

        # Map user_id to user if provided
        if "user_id" in data:
            data["user"] = data.pop("user_id")

        serializer = MembershipCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        membership = serializer.save()

        logger.info(
            "org_member_added",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            membership_id=str(membership.id),
            user_id=str(membership.user_id),
            org_id=str(membership.org_id),
            team_id=str(membership.team_id) if membership.team_id else None,
            org_roles=membership.org_roles,
        )

        # Re-fetch with related objects for response
        membership = Membership.objects.select_related("user", "org", "team").get(
            id=membership.id
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class OrgMemberDetailView(APIView):
    """
    Remove a member from an organization - org_admin only.

    DELETE /api/v1/orgs/{org_id}/members/{user_id}
        Remove member from organization (delete all memberships for this user in this org).
    """

    permission_classes = [IsAuthenticated, IsOrgAdminForOrg]

    def delete(self, request: Request, org_id, user_id) -> Response:
        """Remove member from organization."""
        claims = getattr(request, "token_claims", {})

        # Find all memberships for this user in this org
        memberships = Membership.objects.filter(user_id=user_id, org_id=org_id)

        if not memberships.exists():
            return Response(
                {"error": "User is not a member of this organization"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get user email for logging
        try:
            user = User.objects.get(id=user_id)
            user_email = user.email
        except User.DoesNotExist:
            user_email = "unknown"

        # Count memberships before deletion
        membership_count = memberships.count()

        # Delete all memberships
        memberships.delete()

        logger.info(
            "org_member_removed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            user_id=str(user_id),
            user_email=user_email,
            org_id=str(org_id),
            memberships_removed=membership_count,
        )

        return Response(
            {
                "message": "Member removed from organization",
                "user_id": str(user_id),
                "memberships_removed": membership_count,
            },
            status=status.HTTP_200_OK,
        )

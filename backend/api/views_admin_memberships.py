"""
REST API views for membership admin management.

Provides CRUD operations for memberships, accessible only to platform_admin users.
"""

import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Membership
from api.permissions import IsPlatformAdmin
from api.serializers_admin import (
    MembershipCreateSerializer,
    MembershipListSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
)

logger = structlog.get_logger(__name__)


class AdminMembershipListCreateView(APIView):
    """
    List and create memberships - platform_admin only.

    GET /api/v1/admin/memberships
        Query parameters:
        - user_id: Filter by user ID
        - org_id: Filter by organization ID
        - team_id: Filter by team ID
        - limit: Number of results to return (default: 50, max: 1000)
        - offset: Number of results to skip (default: 0)

    POST /api/v1/admin/memberships
        Create a new membership.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """List all memberships with filtering and pagination."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_membership_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )

        # Build queryset
        queryset = Membership.objects.select_related("user", "org", "team")

        # Apply filters
        user_id = request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        org_id = request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(org_id=org_id)

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

    def post(self, request: Request) -> Response:
        """Create a new membership."""
        claims = getattr(request, "token_claims", {})

        serializer = MembershipCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        membership = serializer.save()

        logger.info(
            "admin_membership_created",
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


class AdminMembershipDetailView(APIView):
    """
    Get, update, or delete a membership - platform_admin only.

    GET /api/v1/admin/memberships/{membership_id}
        Get membership details.

    PUT /api/v1/admin/memberships/{membership_id}
        Update membership roles.

    DELETE /api/v1/admin/memberships/{membership_id}
        Delete membership.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get_object(self, membership_id):
        """Get membership by ID or return None."""
        try:
            return Membership.objects.select_related("user", "org", "team").get(
                id=membership_id
            )
        except Membership.DoesNotExist:
            return None

    def get(self, request: Request, membership_id) -> Response:
        """Get membership details."""
        membership = self.get_object(membership_id)
        if not membership:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_membership_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            membership_id=str(membership_id),
        )

        serializer = MembershipSerializer(membership)
        return Response(serializer.data)

    def put(self, request: Request, membership_id) -> Response:
        """Update membership roles."""
        membership = self.get_object(membership_id)
        if not membership:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        old_values = {
            "org_roles": membership.org_roles,
            "team_roles": membership.team_roles,
            "team_id": str(membership.team_id) if membership.team_id else None,
        }

        serializer = MembershipUpdateSerializer(membership, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        membership = serializer.save()

        # Log changes
        changes = {}
        new_values = {
            "org_roles": membership.org_roles,
            "team_roles": membership.team_roles,
            "team_id": str(membership.team_id) if membership.team_id else None,
        }
        for field, old_val in old_values.items():
            new_val = new_values[field]
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}

        logger.info(
            "admin_membership_updated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            membership_id=str(membership.id),
            user_id=str(membership.user_id),
            org_id=str(membership.org_id),
            changes=changes,
        )

        # Re-fetch with related objects
        membership = Membership.objects.select_related("user", "org", "team").get(
            id=membership.id
        )
        return Response(MembershipSerializer(membership).data)

    def delete(self, request: Request, membership_id) -> Response:
        """Delete membership."""
        membership = self.get_object(membership_id)
        if not membership:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        user_id = str(membership.user_id)
        org_id = str(membership.org_id)
        team_id = str(membership.team_id) if membership.team_id else None

        # Hard delete
        membership.delete()

        logger.info(
            "admin_membership_deleted",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            membership_id=str(membership_id),
            user_id=user_id,
            org_id=org_id,
            team_id=team_id,
        )

        return Response(
            {"message": "Membership deleted", "membership_id": str(membership_id)},
            status=status.HTTP_200_OK,
        )

"""
REST API views for user admin management.

Provides CRUD operations for users, accessible only to platform_admin users.
Supports both local user creation and OIDC user invitation.
"""

import structlog
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models_local_auth import LocalUserProfile
from api.permissions import IsPlatformAdmin
from api.serializers_admin_users import (
    UserCreateSerializer,
    UserInviteSerializer,
    UserListSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()
logger = structlog.get_logger(__name__)


class AdminUserListCreateView(APIView):
    """
    List and create users - platform_admin only.

    GET /api/v1/admin/users
        Query parameters:
        - search: Search by email, first_name, last_name (case-insensitive)
        - is_active: Filter by active status (true/false)
        - auth_provider: Filter by auth provider (local, oidc)
        - org_id: Filter by organization membership
        - limit: Number of results to return (default: 50, max: 1000)
        - offset: Number of results to skip (default: 0)

    POST /api/v1/admin/users
        Create a new local user with password.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """List all users with filtering and pagination."""
        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_user_list_accessed",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )

        # Build queryset with annotations
        queryset = User.objects.select_related("local_profile").annotate(
            _memberships_count=Count("memberships", distinct=True),
        )

        # Apply filters
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        auth_provider = request.query_params.get("auth_provider")
        if auth_provider:
            queryset = queryset.filter(local_profile__auth_provider=auth_provider)

        org_id = request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(memberships__org_id=org_id).distinct()

        # Order by date_joined descending
        queryset = queryset.order_by("-date_joined")

        # Pagination
        limit = min(int(request.query_params.get("limit", 50)), 1000)
        offset = int(request.query_params.get("offset", 0))

        total_count = queryset.count()
        results = queryset[offset : offset + limit]

        serializer = UserListSerializer(results, many=True)

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )

    def post(self, request: Request) -> Response:
        """Create a new local user."""
        claims = getattr(request, "token_claims", {})

        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        logger.info(
            "admin_user_created",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            user_id=str(user.id),
            user_email=user.email,
            auth_provider="local",
        )

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(APIView):
    """
    Get, update, or deactivate a user - platform_admin only.

    GET /api/v1/admin/users/{user_id}
        Get user details including memberships.

    PUT /api/v1/admin/users/{user_id}
        Update user details.

    DELETE /api/v1/admin/users/{user_id}
        Deactivate user (set is_active=False).
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get_object(self, user_id):
        """Get user by ID or return None."""
        try:
            return User.objects.select_related("local_profile").get(id=user_id)
        except User.DoesNotExist:
            return None

    def get(self, request: Request, user_id) -> Response:
        """Get user details."""
        user = self.get_object(user_id)
        if not user:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_user_detail_accessed",
            actor_id=claims.get("sub", "unknown"),
            user_id=str(user_id),
        )

        serializer = UserSerializer(user)
        return Response(serializer.data)

    def put(self, request: Request, user_id) -> Response:
        """Update user."""
        user = self.get_object(user_id)
        if not user:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        old_values = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
        }

        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # Log changes
        changes = {}
        for field, old_val in old_values.items():
            new_val = getattr(user, field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}

        logger.info(
            "admin_user_updated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            user_id=str(user.id),
            user_email=user.email,
            changes=changes,
        )

        return Response(UserSerializer(user).data)

    def delete(self, request: Request, user_id) -> Response:
        """Deactivate user (soft delete)."""
        user = self.get_object(user_id)
        if not user:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})

        # Soft delete by setting is_active to False
        old_status = user.is_active
        user.is_active = False
        user.save(update_fields=["is_active"])

        logger.info(
            "admin_user_deactivated",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            user_id=str(user.id),
            user_email=user.email,
            old_status=old_status,
        )

        return Response(
            {"message": "User deactivated", "user_id": str(user.id)},
            status=status.HTTP_200_OK,
        )


class AdminUserInviteView(APIView):
    """
    Invite an OIDC user - platform_admin only.

    POST /api/v1/admin/users/invite
        Pre-provision a user for OIDC login.
        Optionally assign to an organization.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request: Request) -> Response:
        """Invite a new OIDC user."""
        claims = getattr(request, "token_claims", {})

        serializer = UserInviteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        logger.info(
            "admin_user_invited",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            user_id=str(user.id),
            user_email=user.email,
            auth_provider="oidc",
            org_id=str(request.data.get("org_id")) if request.data.get("org_id") else None,
        )

        # TODO: Send invite email

        return Response(
            {
                "message": "User invited successfully",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminUserResendInviteView(APIView):
    """
    Resend invite email to an OIDC user - platform_admin only.

    POST /api/v1/admin/users/{user_id}/resend-invite
        Resend the invite email for pending OIDC users.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request: Request, user_id) -> Response:
        """Resend invite email."""
        try:
            user = User.objects.select_related("local_profile").get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is an OIDC user with pending verification
        if not hasattr(user, "local_profile"):
            return Response(
                {"error": "User does not have a local profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.local_profile.auth_provider != "oidc":
            return Response(
                {"error": "Resend invite is only available for OIDC users"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.local_profile.email_verified:
            return Response(
                {"error": "User has already completed their registration"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_user_invite_resent",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            user_id=str(user.id),
            user_email=user.email,
        )

        # TODO: Send invite email

        return Response(
            {"message": "Invite email resent successfully"},
            status=status.HTTP_200_OK,
        )


class AdminUserMembershipsView(APIView):
    """
    List user memberships - platform_admin only.

    GET /api/v1/admin/users/{user_id}/memberships
        List all organization and team memberships for a user.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request, user_id) -> Response:
        """List user memberships."""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        claims = getattr(request, "token_claims", {})
        logger.info(
            "admin_user_memberships_accessed",
            actor_id=claims.get("sub", "unknown"),
            user_id=str(user_id),
        )

        from api.serializers_admin_users import UserMembershipSerializer

        memberships = user.memberships.select_related("org", "team").all()
        serializer = UserMembershipSerializer(memberships, many=True)

        return Response(
            {
                "user_id": str(user_id),
                "user_email": user.email,
                "count": len(serializer.data),
                "memberships": serializer.data,
            }
        )

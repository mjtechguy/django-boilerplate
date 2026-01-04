"""
REST API views for User API Key management.

Allows authenticated users to create, list, and revoke their own API keys.
API keys provide an alternative authentication method to JWT tokens.
"""
import structlog
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models_api_keys import UserAPIKey
from api.throttling_api_keys import APIKeyCreationThrottle, get_user_api_key_quota

logger = structlog.get_logger(__name__)


class UserAPIKeyListView(generics.ListAPIView):
    """
    GET /api/v1/me/api-keys - List current user's API keys

    Returns a list of the user's API keys with metadata (prefix, name, created, revoked).
    Does NOT return the full key - that's only shown once at creation.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List user's API keys."""
        api_keys = UserAPIKey.objects.filter(user=request.user).order_by("-created")

        keys_data = [
            {
                "id": str(key.id),
                "prefix": key.prefix,
                "name": key.name,
                "created": key.created,
                "revoked": key.revoked,
            }
            for key in api_keys
        ]

        logger.info(
            "api_keys_listed",
            user_id=request.user.id,
            count=len(keys_data),
        )

        return Response({"api_keys": keys_data}, status=status.HTTP_200_OK)


class UserAPIKeyCreateView(APIView):
    """
    POST /api/v1/me/api-keys - Create a new API key

    Request body:
    {
        "name": "My API Key"  # Optional descriptive name
    }

    Response:
    {
        "id": "uuid",
        "name": "My API Key",
        "key": "abc123.xyz789",  # ONLY returned once!
        "prefix": "abc123",
        "created": "2024-01-01T00:00:00Z",
        "quota": {
            "active_keys": 3,
            "max_keys": 10,
            "remaining": 7
        }
    }
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [APIKeyCreationThrottle]

    def post(self, request):
        """Create a new API key for the current user."""
        # Check quota before creating key
        max_keys = get_user_api_key_quota(request.user)
        active_keys_count = UserAPIKey.objects.filter(
            user=request.user,
            revoked=False
        ).count()

        # -1 means unlimited (enterprise tier)
        if max_keys != -1 and active_keys_count >= max_keys:
            logger.warning(
                "api_key_creation_quota_exceeded",
                user_id=request.user.id,
                active_keys=active_keys_count,
                max_keys=max_keys,
            )
            return Response(
                {
                    "error": f"API key quota exceeded. You have {active_keys_count} active keys and your limit is {max_keys}."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        name = request.data.get("name", "")

        # Create the API key
        api_key, key = UserAPIKey.objects.create_key(
            user=request.user,
            name=name or f"API Key {UserAPIKey.objects.filter(user=request.user).count() + 1}",
        )

        # Update active keys count after creation
        active_keys_count = UserAPIKey.objects.filter(
            user=request.user,
            revoked=False
        ).count()

        logger.info(
            "api_key_created",
            user_id=request.user.id,
            key_id=str(api_key.id),
            key_name=api_key.name,
            key_prefix=api_key.prefix,
            active_keys=active_keys_count,
            max_keys=max_keys,
        )

        return Response(
            {
                "id": str(api_key.id),
                "name": api_key.name,
                "key": key,  # Full key - only shown once!
                "prefix": api_key.prefix,
                "created": api_key.created,
                "quota": {
                    "active_keys": active_keys_count,
                    "max_keys": max_keys,
                    "remaining": max_keys - active_keys_count if max_keys != -1 else -1,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserAPIKeyRevokeView(APIView):
    """
    DELETE /api/v1/me/api-keys/{id} - Revoke an API key

    Marks the key as revoked. Revoked keys cannot be used for authentication.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, key_id):
        """Revoke a user's API key."""
        try:
            api_key = UserAPIKey.objects.get(id=key_id, user=request.user)
        except UserAPIKey.DoesNotExist:
            return Response(
                {"error": "API key not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if api_key.revoked:
            return Response(
                {"error": "API key already revoked"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Revoke the key
        api_key.revoked = True
        api_key.save()

        logger.info(
            "api_key_revoked",
            user_id=request.user.id,
            key_id=str(api_key.id),
            key_name=api_key.name,
            key_prefix=api_key.prefix,
        )

        return Response(
            {"message": "API key revoked successfully"},
            status=status.HTTP_200_OK,
        )

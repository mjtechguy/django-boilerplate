"""
REST API views for S3-style Access Key management.

Allows authenticated users to create, list, and revoke access key pairs.
"""

import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models_access_keys import AccessKeyPair

logger = structlog.get_logger(__name__)


class AccessKeyListView(APIView):
    """
    GET /api/v1/me/access-keys - List current user's access keys

    Returns access key pairs with metadata. Does NOT return secrets.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List user's access keys."""
        access_keys = AccessKeyPair.objects.filter(user=request.user)

        keys_data = [
            {
                "id": key.id,
                "access_key_id": key.access_key_id,
                "name": key.name,
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "revoked": key.revoked,
            }
            for key in access_keys
        ]

        logger.info(
            "access_keys_listed",
            user_id=request.user.id,
            count=len(keys_data),
        )

        return Response({"access_keys": keys_data}, status=status.HTTP_200_OK)


class AccessKeyCreateView(APIView):
    """
    POST /api/v1/me/access-keys - Create a new access key pair

    Request body:
    {
        "name": "My Access Key"  # Optional
    }

    Response includes the secret_access_key - ONLY shown once!
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a new access key pair."""
        name = request.data.get("name", "")

        key_pair, secret = AccessKeyPair.objects.create_key_pair(
            user=request.user,
            name=name,
        )

        logger.info(
            "access_key_created",
            user_id=request.user.id,
            access_key_id=key_pair.access_key_id,
            key_name=key_pair.name,
        )

        return Response(
            {
                "id": key_pair.id,
                "access_key_id": key_pair.access_key_id,
                "secret_access_key": secret,  # Only shown once!
                "name": key_pair.name,
                "created_at": key_pair.created_at,
                "message": "Save your secret access key - it will not be shown again!",
            },
            status=status.HTTP_201_CREATED,
        )


class AccessKeyRevokeView(APIView):
    """
    DELETE /api/v1/me/access-keys/{id} - Revoke an access key

    Revoked keys cannot be used for authentication.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, key_id):
        """Revoke an access key pair."""
        try:
            access_key = AccessKeyPair.objects.get(id=key_id, user=request.user)
        except AccessKeyPair.DoesNotExist:
            return Response(
                {"error": "Access key not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if access_key.revoked:
            return Response(
                {"error": "Access key already revoked"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_key.revoked = True
        access_key.save()

        logger.info(
            "access_key_revoked",
            user_id=request.user.id,
            access_key_id=access_key.access_key_id,
            key_name=access_key.name,
        )

        return Response(
            {"message": "Access key revoked successfully"},
            status=status.HTTP_200_OK,
        )

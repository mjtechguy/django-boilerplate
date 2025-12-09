"""
API Key-based authentication permissions.

Provides permission classes that allow API access using API keys
in addition to JWT authentication.
"""
from typing import Any

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import BaseHasAPIKey

from api.models_api_keys import UserAPIKey

User = get_user_model()


class HasUserAPIKey(BaseHasAPIKey):
    """
    Permission class that checks for valid API key in request headers.

    When a valid key is found, sets request.user to the associated user.
    This allows downstream permission checks and views to work seamlessly.
    """

    model = UserAPIKey

    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        """
        Check if request contains a valid API key and populate request.user.

        The API key should be provided in the Authorization header as:
        Authorization: Api-Key YOUR_KEY_HERE
        """
        has_perm = super().has_permission(request, view)

        if has_perm:
            # Extract user from the API key and set on request
            key = self.get_key(request)
            if key:
                api_key = UserAPIKey.objects.get_from_key(key)
                if api_key:
                    request.user = api_key.user

        return has_perm


class IsAuthenticatedOrHasUserAPIKey(IsAuthenticated):
    """
    Hybrid permission class that accepts either JWT authentication or valid API key.

    This allows endpoints to be accessed via:
    1. JWT token (Authorization: Bearer TOKEN)
    2. API Key (Authorization: Api-Key KEY)
    """

    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        # First check if user is authenticated via JWT
        if super().has_permission(request, view):
            return True

        # Fall back to API key authentication
        api_key_permission = HasUserAPIKey()
        return api_key_permission.has_permission(request, view)

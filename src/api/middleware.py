"""WebSocket authentication middleware for Django Channels."""
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from api.auth import KeycloakJWTAuthentication

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication in WebSocket connections.

    Extracts JWT token from:
    1. Query string: ?token=<jwt>
    2. Headers: Authorization: Bearer <jwt>

    Validates with Keycloak and sets scope["user"] and scope["token_claims"].
    """

    def __init__(self, inner):
        super().__init__(inner)
        self.auth = KeycloakJWTAuthentication()

    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)

        # Extract token from query string or headers
        token = self._get_token_from_scope(scope)

        if token:
            # Validate token and get user
            user, claims = await self._authenticate_token(token)
            scope["user"] = user
            scope["token_claims"] = claims
        else:
            scope["user"] = AnonymousUser()
            scope["token_claims"] = {}

        return await super().__call__(scope, receive, send)

    def _get_token_from_scope(self, scope: Dict[str, Any]) -> Optional[str]:
        """Extract JWT token from query string or headers."""
        # Try query string first: ?token=<jwt>
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            params = parse_qs(query_string)
            if "token" in params:
                return params["token"][0]

        # Try headers: Authorization: Bearer <jwt>
        headers = dict(scope.get("headers", []))
        if b"authorization" in headers:
            auth_header = headers[b"authorization"].decode("utf-8")
            if auth_header.startswith("Bearer "):
                return auth_header[7:]  # Remove "Bearer " prefix

        return None

    @database_sync_to_async
    def _authenticate_token(self, token: str) -> tuple[User, Dict[str, Any]]:
        """
        Validate JWT token and return user and claims.

        Uses the same KeycloakJWTAuthentication as DRF for consistency.
        """
        try:
            claims = self.auth._validate_token(token)  # noqa: SLF001

            # Get or create shadow Django user
            user, _ = User.objects.get_or_create(
                username=claims["sub"],
                defaults={"email": claims.get("email", "")}
            )
            user.backend = "django.contrib.auth.backends.ModelBackend"

            return user, claims
        except Exception:  # noqa: BLE001
            # If validation fails, return AnonymousUser
            return AnonymousUser(), {}

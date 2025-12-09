"""
REST API views for Social OAuth authentication.

Provides API endpoints for social login (Google, GitHub) that work with SPAs.
Returns JWT tokens instead of session-based authentication.
"""

import structlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.local_jwt import generate_access_token, generate_refresh_token

logger = structlog.get_logger(__name__)
User = get_user_model()


def get_enabled_providers() -> list:
    """Get list of enabled social providers from settings."""
    providers = []

    if getattr(settings, "GOOGLE_CLIENT_ID", None):
        providers.append({
            "id": "google",
            "name": "Google",
        })

    if getattr(settings, "GITHUB_CLIENT_ID", None):
        providers.append({
            "id": "github",
            "name": "GitHub",
        })

    return providers


class SocialProvidersView(APIView):
    """
    GET /api/v1/auth/social/providers - List available social providers

    Returns list of configured OAuth providers.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """List available social providers."""
        providers = get_enabled_providers()
        return Response({"providers": providers})


class SocialLoginView(APIView):
    """
    GET /api/v1/auth/social/{provider}/login - Get OAuth login URL

    Returns the OAuth authorization URL for the specified provider.
    The frontend should redirect the user to this URL.
    """

    permission_classes = [AllowAny]

    def get(self, request, provider):
        """Get OAuth login URL for provider."""
        # Validate provider
        enabled = {p["id"] for p in get_enabled_providers()}
        if provider not in enabled:
            return Response(
                {"error": f"Provider '{provider}' is not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get callback URL
        callback_url = request.build_absolute_uri(f"/api/v1/auth/social/callback?provider={provider}")

        # Get frontend redirect URL (where to send user after OAuth)
        redirect_url = request.query_params.get("redirect", "/")

        # Store redirect URL in session for callback
        request.session["social_auth_redirect"] = redirect_url

        # Build OAuth URL based on provider
        if provider == "google":
            auth_url = self._get_google_auth_url(callback_url)
        elif provider == "github":
            auth_url = self._get_github_auth_url(callback_url)
        else:
            return Response(
                {"error": "Provider not supported"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "social_login_initiated",
            provider=provider,
            callback_url=callback_url,
        )

        return Response({"auth_url": auth_url})

    def _get_google_auth_url(self, callback_url: str) -> str:
        """Build Google OAuth URL."""
        import urllib.parse

        client_id = settings.GOOGLE_CLIENT_ID
        scope = "openid email profile"

        params = {
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "select_account",
        }

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base_url}?{urllib.parse.urlencode(params)}"

    def _get_github_auth_url(self, callback_url: str) -> str:
        """Build GitHub OAuth URL."""
        import urllib.parse

        client_id = settings.GITHUB_CLIENT_ID
        scope = "user:email"

        params = {
            "client_id": client_id,
            "redirect_uri": callback_url,
            "scope": scope,
        }

        base_url = "https://github.com/login/oauth/authorize"
        return f"{base_url}?{urllib.parse.urlencode(params)}"


class SocialCallbackView(APIView):
    """
    GET /api/v1/auth/social/callback - OAuth callback handler

    Handles the OAuth callback, exchanges code for tokens,
    creates/links user, and returns JWT tokens.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Handle OAuth callback."""
        provider = request.query_params.get("provider")
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error:
            return Response(
                {"error": f"OAuth error: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code:
            return Response(
                {"error": "No authorization code provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not provider:
            return Response(
                {"error": "No provider specified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Exchange code for user info
        try:
            if provider == "google":
                user_info = self._exchange_google_code(request, code)
            elif provider == "github":
                user_info = self._exchange_github_code(request, code)
            else:
                return Response(
                    {"error": "Unsupported provider"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.error(
                "social_auth_exchange_failed",
                provider=provider,
                error=str(e),
            )
            return Response(
                {"error": "Failed to authenticate with provider"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Get or create user
        user = self._get_or_create_user(provider, user_info)

        if not user:
            return Response(
                {"error": "Failed to create user account"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Generate JWT tokens
        roles = ["user"]
        if hasattr(user, "local_profile"):
            roles = user.local_profile.roles

        access_token = generate_access_token(user, roles=roles)
        refresh_token = generate_refresh_token(user)

        # Get redirect URL from session
        redirect_url = request.session.pop("social_auth_redirect", "/")

        logger.info(
            "social_login_success",
            provider=provider,
            user_id=user.id,
            user_email=user.email,
        )

        # Return tokens with redirect URL
        return Response({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "redirect_url": redirect_url,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.get_full_name() or user.username,
            },
        })

    def _exchange_google_code(self, request, code: str) -> dict:
        """Exchange Google auth code for user info."""
        import requests

        # Build callback URL (must match the one used in login)
        callback_url = request.build_absolute_uri("/api/v1/auth/social/callback?provider=google")

        # Exchange code for tokens
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        # Get user info
        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        user_response.raise_for_status()
        user_info = user_response.json()

        return {
            "provider_id": user_info["id"],
            "email": user_info["email"],
            "name": user_info.get("name", ""),
            "first_name": user_info.get("given_name", ""),
            "last_name": user_info.get("family_name", ""),
            "picture": user_info.get("picture", ""),
        }

    def _exchange_github_code(self, request, code: str) -> dict:
        """Exchange GitHub auth code for user info."""
        import requests

        # Exchange code for access token
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        if "error" in tokens:
            raise ValueError(tokens.get("error_description", tokens["error"]))

        access_token = tokens["access_token"]

        # Get user info
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )
        user_response.raise_for_status()
        user_info = user_response.json()

        # Get user email (might be private)
        email = user_info.get("email")
        if not email:
            email_response = requests.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10,
            )
            email_response.raise_for_status()
            emails = email_response.json()
            # Get primary email
            for e in emails:
                if e.get("primary"):
                    email = e["email"]
                    break
            if not email and emails:
                email = emails[0]["email"]

        # Parse name
        name = user_info.get("name", "") or user_info.get("login", "")
        parts = name.split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        return {
            "provider_id": str(user_info["id"]),
            "email": email,
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "picture": user_info.get("avatar_url", ""),
        }

    @transaction.atomic
    def _get_or_create_user(self, provider: str, user_info: dict):
        """Get or create user from social auth info."""
        from api.models_social_auth import SocialAccount

        email = user_info.get("email")
        if not email:
            logger.error("social_auth_no_email", provider=provider)
            return None

        provider_id = user_info["provider_id"]

        # Check if social account already exists
        try:
            social_account = SocialAccount.objects.get(
                provider=provider,
                provider_id=provider_id,
            )
            # Update user info
            user = social_account.user
            user.first_name = user_info.get("first_name", "") or user.first_name
            user.last_name = user_info.get("last_name", "") or user.last_name
            user.save(update_fields=["first_name", "last_name"])
            return user
        except SocialAccount.DoesNotExist:
            pass

        # Check if user with this email exists
        try:
            user = User.objects.get(email__iexact=email)
            # Link social account to existing user
            SocialAccount.objects.create(
                user=user,
                provider=provider,
                provider_id=provider_id,
            )
            return user
        except User.DoesNotExist:
            pass

        # Create new user
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
        )

        # Create social account link
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_id=provider_id,
        )

        # Create local profile with default role
        from api.models_local_auth import LocalUserProfile

        LocalUserProfile.objects.get_or_create(
            user=user,
            defaults={
                "auth_provider": f"social:{provider}",
                "email_verified": True,  # Social auth emails are pre-verified
                "roles": ["user"],
            },
        )

        return user


class SocialAccountsView(APIView):
    """
    GET /api/v1/me/social-accounts - List connected social accounts
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List user's connected social accounts."""
        from api.models_social_auth import SocialAccount

        accounts = SocialAccount.objects.filter(user=request.user)
        data = [
            {
                "id": acc.id,
                "provider": acc.provider,
                "connected_at": acc.created_at,
            }
            for acc in accounts
        ]

        return Response({"accounts": data})


class SocialAccountDisconnectView(APIView):
    """
    DELETE /api/v1/me/social-accounts/{id} - Disconnect a social account
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, account_id):
        """Disconnect a social account."""
        from api.models_social_auth import SocialAccount

        try:
            account = SocialAccount.objects.get(id=account_id, user=request.user)
        except SocialAccount.DoesNotExist:
            return Response(
                {"error": "Social account not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user has another auth method
        has_password = (
            hasattr(request.user, "local_profile")
            and request.user.local_profile.password_hash
        )
        other_social_count = SocialAccount.objects.filter(user=request.user).exclude(id=account_id).count()

        if not has_password and other_social_count == 0:
            return Response(
                {"error": "Cannot disconnect last authentication method. Set a password first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = account.provider
        account.delete()

        logger.info(
            "social_account_disconnected",
            user_id=request.user.id,
            provider=provider,
        )

        return Response({"message": f"{provider} account disconnected"})

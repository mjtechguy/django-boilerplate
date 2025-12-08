"""
Views for local authentication endpoints.

This module provides API endpoints for registration, login, logout,
token refresh, and user profile management.
"""

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from api.local_jwt import generate_access_token, generate_refresh_token
from api.models_local_auth import LocalUserProfile, RefreshToken
from api.serializers_local_auth import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    TokenRefreshSerializer,
    TokenResponseSerializer,
    UserProfileSerializer,
)

User = get_user_model()


class RegistrationRateThrottle(AnonRateThrottle):
    """Rate limit for registration to prevent abuse."""

    rate = "10/hour"


class LoginRateThrottle(AnonRateThrottle):
    """Rate limit for login to prevent brute force."""

    rate = "20/minute"


class RegisterView(APIView):
    """
    User registration endpoint.

    POST /api/v1/auth/register
    Creates a new user account and sends a verification email.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]

    @transaction.atomic
    def post(self, request):
        # Check if local auth is enabled
        if not getattr(settings, "LOCAL_AUTH_ENABLED", True):
            return Response(
                {"error": "Local authentication is not enabled"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Create the user
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=None,  # We don't use Django's password field
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )

        # Create local profile with password
        profile = LocalUserProfile.objects.create(
            user=user,
            auth_provider="local",
            roles=["user"],  # Default role
        )
        profile.set_password(data["password"])
        profile.save()

        # Generate email verification token
        token = profile.generate_email_verification_token()

        # Send verification email
        self._send_verification_email(user, token)

        return Response(
            {
                "message": "Registration successful. Please check your email to verify your account.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )

    def _send_verification_email(self, user: User, token: str) -> None:
        """Send email verification email."""
        from api.email import send_email

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        verification_url = f"{frontend_url}/verify-email?token={token}"

        send_email(
            to=[user.email],
            subject="Verify your email address",
            template="email/verify_email.html",
            context={
                "user": user,
                "verification_url": verification_url,
            },
        )


class LoginView(APIView):
    """
    User login endpoint.

    POST /api/v1/auth/login
    Authenticates the user and returns access and refresh tokens.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        # Check if local auth is enabled
        if not getattr(settings, "LOCAL_AUTH_ENABLED", True):
            return Response(
                {"error": "Local authentication is not enabled"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        email = data["email"].lower()
        password = data["password"]

        # Find user
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if user has local profile
        try:
            profile = user.local_profile
        except LocalUserProfile.DoesNotExist:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if account is locked
        ip_address = self._get_client_ip(request)
        if profile.is_locked():
            return Response(
                {"error": "Account is temporarily locked. Please try again later."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Verify password
        if not profile.check_password(password):
            profile.record_login_attempt(success=False, ip_address=ip_address)
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if user is active
        if not user.is_active:
            return Response(
                {"error": "Account is disabled"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check email verification if required
        email_verification_required = getattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)
        if email_verification_required and not profile.email_verified:
            return Response(
                {"error": "Please verify your email before logging in"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Record successful login
        profile.record_login_attempt(success=True, ip_address=ip_address)

        # Generate tokens
        access_token = generate_access_token(user, roles=profile.roles)
        refresh_token = generate_refresh_token(user)

        # Store refresh token
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        RefreshToken.create_for_user(
            user=user,
            token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        access_ttl = getattr(settings, "LOCAL_AUTH_ACCESS_TOKEN_TTL", 3600)

        return Response(
            TokenResponseSerializer(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": access_ttl,
                }
            ).data
        )

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class LogoutView(APIView):
    """
    User logout endpoint.

    POST /api/v1/auth/logout
    Revokes the refresh token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if refresh_token:
            # Revoke the specific refresh token
            token_obj = RefreshToken.validate_token(refresh_token)
            if token_obj:
                token_obj.revoke()
        else:
            # Revoke all refresh tokens for the user
            RefreshToken.revoke_all_for_user(request.user)

        return Response({"message": "Logged out successfully"})


class TokenRefreshView(APIView):
    """
    Token refresh endpoint.

    POST /api/v1/auth/refresh
    Exchanges a valid refresh token for a new access token.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh_token"]

        # Validate refresh token
        token_obj = RefreshToken.validate_token(refresh_token)
        if not token_obj:
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = token_obj.user

        # Check if user is still active
        if not user.is_active:
            token_obj.revoke()
            return Response(
                {"error": "Account is disabled"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get roles from local profile
        roles = []
        if hasattr(user, "local_profile"):
            roles = user.local_profile.roles

        # Generate new access token
        access_token = generate_access_token(user, roles=roles)
        access_ttl = getattr(settings, "LOCAL_AUTH_ACCESS_TOKEN_TTL", 3600)

        return Response(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": access_ttl,
            }
        )


class CurrentUserView(APIView):
    """
    Get current user info.

    GET /api/v1/auth/me
    Returns the current user's profile information.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """
    Change password for authenticated user.

    POST /api/v1/auth/change-password
    Changes the password for a locally authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if user has local profile
        if not hasattr(request.user, "local_profile"):
            return Response(
                {"error": "Password change is only available for locally authenticated users"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = request.user.local_profile
        data = serializer.validated_data

        # Verify current password
        if not profile.check_password(data["current_password"]):
            return Response(
                {"error": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        profile.set_password(data["new_password"])
        profile.save()

        # Revoke all existing refresh tokens
        RefreshToken.revoke_all_for_user(request.user)

        return Response({"message": "Password changed successfully"})

"""
Views for password reset and email verification.

These endpoints handle the password reset flow and email verification.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from api.models_local_auth import LocalUserProfile, RefreshToken
from api.serializers_local_auth import (
    EmailVerificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendVerificationSerializer,
)

User = get_user_model()


class PasswordResetRateThrottle(AnonRateThrottle):
    """Rate limit for password reset to prevent abuse."""

    rate = "5/hour"


class EmailVerificationRateThrottle(AnonRateThrottle):
    """Rate limit for email verification resend."""

    rate = "5/hour"


class PasswordResetRequestView(APIView):
    """
    Request a password reset email.

    POST /api/v1/auth/password-reset
    Sends a password reset email if the user exists.
    Always returns success to prevent email enumeration.
    """

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()

        # Always return success to prevent email enumeration
        response_message = {
            "message": "If an account with that email exists, a password reset link has been sent."
        }

        try:
            user = User.objects.get(email__iexact=email)
            profile = user.local_profile
        except (User.DoesNotExist, LocalUserProfile.DoesNotExist):
            return Response(response_message)

        # Generate password reset token
        token = profile.generate_password_reset_token()

        # Send password reset email
        self._send_reset_email(user, token)

        return Response(response_message)

    def _send_reset_email(self, user: User, token: str) -> None:
        """Send password reset email."""
        from api.email import send_email

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={token}"

        send_email(
            to=[user.email],
            subject="Reset your password",
            template="email/password_reset.html",
            context={
                "user": user,
                "reset_url": reset_url,
            },
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token.

    POST /api/v1/auth/password-reset/confirm
    Sets a new password using the reset token.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        token = data["token"]
        new_password = data["password"]

        # Find profile with this reset token
        try:
            profile = LocalUserProfile.objects.get(password_reset_token=token)
        except LocalUserProfile.DoesNotExist:
            return Response(
                {"error": "Invalid or expired reset token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify token is valid and not expired
        if not profile.verify_password_reset_token(token):
            return Response(
                {"error": "Invalid or expired reset token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        profile.set_password(new_password)
        profile.clear_password_reset_token()

        # Revoke all refresh tokens for security
        RefreshToken.revoke_all_for_user(profile.user)

        return Response({"message": "Password has been reset successfully"})


class EmailVerificationView(APIView):
    """
    Verify email address.

    POST /api/v1/auth/verify-email
    GET /api/v1/auth/verify-email?token=xxx
    Verifies the user's email address using the token.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Handle verification via URL parameter."""
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"error": "Verification token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._verify_email(token)

    def post(self, request):
        """Handle verification via POST body."""
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._verify_email(serializer.validated_data["token"])

    def _verify_email(self, token: str):
        """Verify email with the provided token."""
        try:
            profile = LocalUserProfile.objects.get(email_verification_token=token)
        except LocalUserProfile.DoesNotExist:
            return Response(
                {"error": "Invalid or expired verification token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if profile.verify_email(token):
            return Response({"message": "Email verified successfully"})

        return Response(
            {"error": "Invalid or expired verification token"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ResendVerificationView(APIView):
    """
    Resend email verification.

    POST /api/v1/auth/resend-verification
    Resends the email verification link.
    """

    permission_classes = [AllowAny]
    throttle_classes = [EmailVerificationRateThrottle]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()

        # Always return success to prevent email enumeration
        response_message = {
            "message": "If an unverified account with that email exists, a verification link has been sent."
        }

        try:
            user = User.objects.get(email__iexact=email)
            profile = user.local_profile
        except (User.DoesNotExist, LocalUserProfile.DoesNotExist):
            return Response(response_message)

        # Don't send if already verified
        if profile.email_verified:
            return Response(response_message)

        # Generate new verification token
        token = profile.generate_email_verification_token()

        # Send verification email
        self._send_verification_email(user, token)

        return Response(response_message)

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

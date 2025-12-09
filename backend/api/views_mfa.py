"""
REST API views for TOTP MFA management.

Endpoints for setting up, verifying, and managing TOTP multi-factor authentication.
"""

import base64
import io

import qrcode
import structlog
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.local_jwt import generate_access_token, generate_refresh_token
from api.models_mfa import MFAToken, TOTPDevice
from api.throttling_mfa import (
    MFAIPThrottle,
    MFATokenThrottle,
    MFAUserThrottle,
    increment_mfa_failures,
)

logger = structlog.get_logger(__name__)


class MFASetupView(APIView):
    """
    POST /api/v1/auth/mfa/setup - Begin MFA setup

    Returns TOTP secret and QR code for authenticator app setup.
    Device is not confirmed until code is verified.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Initialize MFA setup."""
        user = request.user

        # Check if user already has MFA
        if hasattr(user, "totp_device") and user.totp_device.confirmed:
            return Response(
                {"error": "MFA is already enabled. Disable it first to set up again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete any unconfirmed device
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()

        # Create new device
        device, backup_codes = TOTPDevice.objects.create_device(user=user)

        # Generate QR code
        provisioning_uri = device.get_provisioning_uri()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Convert to base64 image
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        logger.info(
            "mfa_setup_initiated",
            user_id=user.id,
            user_email=user.email,
        )

        return Response(
            {
                "secret": device.secret,
                "qr_code": f"data:image/png;base64,{qr_base64}",
                "provisioning_uri": provisioning_uri,
                "backup_codes": backup_codes,
                "message": "Scan the QR code with your authenticator app, then confirm with a code.",
            },
            status=status.HTTP_200_OK,
        )


class MFAConfirmView(APIView):
    """
    POST /api/v1/auth/mfa/confirm - Confirm MFA setup

    Verifies the TOTP code to confirm MFA is working before enabling it.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Confirm MFA setup with TOTP code."""
        user = request.user
        code = request.data.get("code", "")

        if not code:
            return Response(
                {"error": "TOTP code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get unconfirmed device
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=False)
        except TOTPDevice.DoesNotExist:
            return Response(
                {"error": "No pending MFA setup. Start setup first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify code
        if not device.verify_code(code):
            logger.warning(
                "mfa_confirm_failed",
                user_id=user.id,
                reason="invalid_code",
            )
            return Response(
                {"error": "Invalid TOTP code. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Confirm device
        device.confirmed = True
        device.last_used_at = timezone.now()
        device.save(update_fields=["confirmed", "last_used_at"])

        logger.info(
            "mfa_enabled",
            user_id=user.id,
            user_email=user.email,
        )

        return Response(
            {
                "message": "MFA has been enabled successfully.",
                "backup_codes_remaining": device.remaining_backup_codes(),
            },
            status=status.HTTP_200_OK,
        )


class MFADisableView(APIView):
    """
    POST /api/v1/auth/mfa/disable - Disable MFA

    Requires current TOTP code to disable MFA.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Disable MFA."""
        user = request.user
        code = request.data.get("code", "")

        if not code:
            return Response(
                {"error": "TOTP code is required to disable MFA"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get confirmed device
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=True)
        except TOTPDevice.DoesNotExist:
            return Response(
                {"error": "MFA is not enabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify code (allow backup code too)
        if not device.verify_code(code) and not device.verify_backup_code(code):
            logger.warning(
                "mfa_disable_failed",
                user_id=user.id,
                reason="invalid_code",
            )
            return Response(
                {"error": "Invalid code. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete device
        device.delete()

        logger.info(
            "mfa_disabled",
            user_id=user.id,
            user_email=user.email,
        )

        return Response(
            {"message": "MFA has been disabled."},
            status=status.HTTP_200_OK,
        )


class MFABackupCodesView(APIView):
    """
    POST /api/v1/auth/mfa/backup-codes - Regenerate backup codes

    Requires current TOTP code. Returns new backup codes (invalidates old ones).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Regenerate backup codes."""
        user = request.user
        code = request.data.get("code", "")

        if not code:
            return Response(
                {"error": "TOTP code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get confirmed device
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=True)
        except TOTPDevice.DoesNotExist:
            return Response(
                {"error": "MFA is not enabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify code
        if not device.verify_code(code):
            logger.warning(
                "mfa_backup_regen_failed",
                user_id=user.id,
                reason="invalid_code",
            )
            return Response(
                {"error": "Invalid TOTP code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Regenerate codes
        new_codes = device.regenerate_backup_codes()

        logger.info(
            "mfa_backup_codes_regenerated",
            user_id=user.id,
        )

        return Response(
            {
                "backup_codes": new_codes,
                "message": "New backup codes generated. Previous codes are now invalid.",
            },
            status=status.HTTP_200_OK,
        )


class MFAStatusView(APIView):
    """
    GET /api/v1/auth/mfa/status - Get MFA status

    Returns whether MFA is enabled and number of remaining backup codes.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get MFA status."""
        user = request.user

        try:
            device = TOTPDevice.objects.get(user=user, confirmed=True)
            return Response(
                {
                    "enabled": True,
                    "backup_codes_remaining": device.remaining_backup_codes(),
                    "last_used_at": device.last_used_at,
                },
                status=status.HTTP_200_OK,
            )
        except TOTPDevice.DoesNotExist:
            return Response(
                {
                    "enabled": False,
                    "backup_codes_remaining": 0,
                    "last_used_at": None,
                },
                status=status.HTTP_200_OK,
            )


class MFAVerifyView(APIView):
    """
    POST /api/v1/auth/mfa/verify - Complete MFA verification during login

    Used after successful password auth when MFA is required.
    Accepts temporary MFA token and TOTP code, returns JWT tokens.

    Rate limited with multi-layer throttling:
    - Per-token: 5 attempts per 15 minutes
    - Per-user: 10 attempts per hour
    - Per-IP: 20 attempts per hour
    """

    permission_classes = [AllowAny]
    throttle_classes = [MFATokenThrottle, MFAUserThrottle, MFAIPThrottle]

    def post(self, request):
        """Verify MFA code and complete login."""
        mfa_token = request.data.get("mfa_token", "")
        code = request.data.get("code", "")

        if not mfa_token or not code:
            return Response(
                {"error": "MFA token and code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find and validate MFA token
        try:
            token_obj = MFAToken.objects.get(token=mfa_token)
        except MFAToken.DoesNotExist:
            return Response(
                {"error": "Invalid or expired MFA token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not token_obj.is_valid():
            return Response(
                {"error": "MFA token has expired. Please login again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = token_obj.user

        # Get TOTP device
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=True)
        except TOTPDevice.DoesNotExist:
            return Response(
                {"error": "MFA is not configured for this user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify code (TOTP or backup)
        code_valid = device.verify_code(code) or device.verify_backup_code(code)

        if not code_valid:
            # Increment throttle counters on failure (not on success - prevents timing attacks)
            increment_mfa_failures(request)
            logger.warning(
                "mfa_login_verify_failed",
                user_id=user.id,
                reason="invalid_code",
            )
            return Response(
                {"error": "Invalid code"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Consume MFA token
        token_obj.consume()

        # Update device last used
        device.last_used_at = timezone.now()
        device.save(update_fields=["last_used_at"])

        # Generate JWT tokens
        # Get roles from user's local profile if available
        roles = []
        if hasattr(user, "local_profile"):
            roles = user.local_profile.roles

        access_token = generate_access_token(user, roles=roles)
        refresh_token = generate_refresh_token(user)

        logger.info(
            "mfa_login_success",
            user_id=user.id,
            user_email=user.email,
        )

        return Response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
            },
            status=status.HTTP_200_OK,
        )

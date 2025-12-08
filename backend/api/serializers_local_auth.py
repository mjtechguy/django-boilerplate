"""
Serializers for local authentication endpoints.

These serializers handle validation for registration, login, token refresh,
password reset, and related authentication operations.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration."""

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        """Validate that the email is not already registered."""
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value: str) -> str:
        """Validate password against Django's password validators."""
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate that passwords match."""
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""

    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
    expires_in = serializers.IntegerField()


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh."""

    refresh_token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_password(self, value: str) -> str:
        """Validate password against Django's password validators."""
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate that passwords match."""
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated user)."""

    current_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_new_password(self, value: str) -> str:
        """Validate new password against Django's password validators."""
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate that new passwords match."""
        if attrs.get("new_password") != attrs.get("new_password_confirm"):
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""

    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending email verification."""

    email = serializers.EmailField()


class UserProfileSerializer(serializers.Serializer):
    """Serializer for user profile (current user info)."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    email_verified = serializers.SerializerMethodField()
    auth_provider = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    def get_email_verified(self, obj) -> bool:
        """Get email verification status."""
        if hasattr(obj, "local_profile"):
            return obj.local_profile.email_verified
        # For OIDC users, email is verified by the IdP
        return True

    def get_auth_provider(self, obj) -> str:
        """Get authentication provider."""
        if hasattr(obj, "local_profile"):
            return obj.local_profile.auth_provider
        return "oidc"

    def get_roles(self, obj) -> list:
        """Get user roles."""
        if hasattr(obj, "local_profile"):
            return obj.local_profile.roles
        # For OIDC users, roles come from JWT claims
        realm_roles = getattr(obj, "realm_roles", [])
        client_roles = getattr(obj, "client_roles", [])
        return list(set(realm_roles + client_roles))

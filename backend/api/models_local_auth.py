"""
Local authentication models for username/password authentication.

This module provides a LocalUserProfile model that stores local auth
credentials alongside the Django User model, using Argon2 for password hashing.
"""

import secrets
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from api.models import TimeStampedModel

User = get_user_model()


def generate_token() -> str:
    """Generate a cryptographically secure token."""
    return secrets.token_urlsafe(48)


class LocalUserProfile(TimeStampedModel):
    """
    Local authentication profile for a user.

    Stores password hash and verification tokens for users who authenticate
    via local username/password instead of (or in addition to) OIDC.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="local_profile",
    )

    # Password is hashed with Argon2
    password_hash = models.CharField(max_length=255)

    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)

    # Password reset
    password_reset_token = models.CharField(max_length=64, blank=True)
    password_reset_sent_at = models.DateTimeField(null=True, blank=True)

    # Authentication provider tracking
    auth_provider = models.CharField(
        max_length=32,
        default="local",
        help_text="Authentication provider: local, oidc, or both",
    )

    # Local roles (used when not using Keycloak)
    roles = models.JSONField(
        default=list,
        blank=True,
        help_text="User roles: platform_admin, org_admin, user, etc.",
    )

    # Failed login tracking
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Local User Profile"
        verbose_name_plural = "Local User Profiles"
        indexes = [
            models.Index(fields=["email_verification_token"]),
            models.Index(fields=["password_reset_token"]),
        ]

    def __str__(self) -> str:
        return f"LocalUserProfile<{self.user.email}>"

    def set_password(self, raw_password: str) -> None:
        """
        Hash and store a password using Argon2.

        Django automatically uses Argon2 when argon2-cffi is installed
        and PASSWORD_HASHERS has Argon2 as the first option.
        """
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """
        Verify a password against the stored hash.

        Returns True if the password matches, False otherwise.
        """
        return check_password(raw_password, self.password_hash)

    def generate_email_verification_token(self) -> str:
        """Generate and store a new email verification token."""
        self.email_verification_token = generate_token()
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=["email_verification_token", "email_verification_sent_at"])
        return self.email_verification_token

    def verify_email(self, token: str) -> bool:
        """
        Verify email with the provided token.

        Returns True if verification succeeded, False otherwise.
        """
        if not self.email_verification_token:
            return False

        # Check token expiry
        if self.email_verification_sent_at:
            token_age = timezone.now() - self.email_verification_sent_at
            ttl = getattr(settings, "EMAIL_VERIFICATION_TOKEN_TTL", 86400)
            if token_age.total_seconds() > ttl:
                return False

        if secrets.compare_digest(self.email_verification_token, token):
            self.email_verified = True
            self.email_verification_token = ""
            self.email_verification_sent_at = None
            self.save(update_fields=[
                "email_verified",
                "email_verification_token",
                "email_verification_sent_at",
            ])
            return True
        return False

    def generate_password_reset_token(self) -> str:
        """Generate and store a new password reset token."""
        self.password_reset_token = generate_token()
        self.password_reset_sent_at = timezone.now()
        self.save(update_fields=["password_reset_token", "password_reset_sent_at"])
        return self.password_reset_token

    def verify_password_reset_token(self, token: str) -> bool:
        """
        Verify a password reset token.

        Returns True if the token is valid and not expired, False otherwise.
        """
        if not self.password_reset_token:
            return False

        # Check token expiry
        if self.password_reset_sent_at:
            token_age = timezone.now() - self.password_reset_sent_at
            ttl = getattr(settings, "PASSWORD_RESET_TOKEN_TTL", 3600)
            if token_age.total_seconds() > ttl:
                return False

        return secrets.compare_digest(self.password_reset_token, token)

    def clear_password_reset_token(self) -> None:
        """Clear the password reset token after use."""
        self.password_reset_token = ""
        self.password_reset_sent_at = None
        self.save(update_fields=["password_reset_token", "password_reset_sent_at"])

    def record_login_attempt(self, success: bool, ip_address: str | None = None) -> None:
        """Record a login attempt and update lockout status."""
        if success:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.last_login_at = timezone.now()
            self.last_login_ip = ip_address
        else:
            self.failed_login_attempts += 1
            max_attempts = getattr(settings, "LOCAL_AUTH_MAX_FAILED_ATTEMPTS", 5)
            lockout_duration = getattr(settings, "LOCAL_AUTH_LOCKOUT_DURATION", 1800)

            if self.failed_login_attempts >= max_attempts:
                self.locked_until = timezone.now() + timezone.timedelta(seconds=lockout_duration)

        self.save(update_fields=[
            "failed_login_attempts",
            "locked_until",
            "last_login_at",
            "last_login_ip",
        ])

    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False


class RefreshToken(TimeStampedModel):
    """
    Store refresh tokens for local authentication.

    Refresh tokens are stored hashed and can be revoked.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Refresh Token"
        verbose_name_plural = "Refresh Tokens"
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"RefreshToken<{self.user.email}>"

    @classmethod
    def create_for_user(
        cls,
        user: User,
        token: str,
        user_agent: str = "",
        ip_address: str | None = None,
    ) -> "RefreshToken":
        """
        Create a new refresh token for a user.

        The raw token is passed in, and we store its hash.
        """
        import hashlib

        ttl = getattr(settings, "LOCAL_AUTH_REFRESH_TOKEN_TTL", 604800)
        expires_at = timezone.now() + timezone.timedelta(seconds=ttl)

        return cls.objects.create(
            user=user,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=expires_at,
            user_agent=user_agent[:255] if user_agent else "",
            ip_address=ip_address,
        )

    @classmethod
    def validate_token(cls, token: str) -> "RefreshToken | None":
        """
        Validate a refresh token and return the RefreshToken object if valid.

        Returns None if the token is invalid, expired, or revoked.
        """
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            refresh_token = cls.objects.get(
                token_hash=token_hash,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            return refresh_token
        except cls.DoesNotExist:
            return None

    def revoke(self) -> None:
        """Revoke this refresh token."""
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    @classmethod
    def revoke_all_for_user(cls, user: User) -> int:
        """
        Revoke all refresh tokens for a user.

        Returns the number of tokens revoked.
        """
        return cls.objects.filter(
            user=user,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Delete expired and revoked tokens.

        Returns the number of tokens deleted.
        """
        count, _ = cls.objects.filter(
            models.Q(expires_at__lt=timezone.now())
            | models.Q(revoked_at__isnull=False)
        ).delete()
        return count

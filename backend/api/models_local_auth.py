"""
Local authentication models for username/password authentication.

This module provides a LocalUserProfile model that stores local auth
credentials alongside the Django User model, using Argon2 for password hashing.
"""

import hashlib
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

    # Stripe billing fields (B2C user-level subscriptions)
    stripe_customer_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Stripe customer ID for user billing"
    )
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Active Stripe subscription ID"
    )
    license_tier = models.CharField(
        max_length=64, default="free",
        help_text="User's subscription tier: free, starter, pro, enterprise"
    )
    feature_flags = models.JSONField(
        default=dict, blank=True,
        help_text="User-specific feature flags from subscription"
    )

    class Meta:
        verbose_name = "Local User Profile"
        verbose_name_plural = "Local User Profiles"
        indexes = [
            models.Index(fields=["email_verification_token"]),
            models.Index(fields=["password_reset_token"]),
            models.Index(fields=["stripe_customer_id"]),
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
        """Generate and store a hashed email verification token."""
        token = generate_token()
        # Store the hash, return the plaintext for the email
        self.email_verification_token = hashlib.sha256(token.encode()).hexdigest()
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=["email_verification_token", "email_verification_sent_at"])
        return token

    def verify_email(self, token: str) -> bool:
        """
        Verify email with the provided token (compares hash).

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

        # Compare hashes using constant-time comparison
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if secrets.compare_digest(self.email_verification_token, token_hash):
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
        """Generate and store a hashed password reset token."""
        token = generate_token()
        # Store the hash, return the plaintext for the email
        self.password_reset_token = hashlib.sha256(token.encode()).hexdigest()
        self.password_reset_sent_at = timezone.now()
        self.save(update_fields=["password_reset_token", "password_reset_sent_at"])
        return token

    def verify_password_reset_token(self, token: str) -> bool:
        """
        Verify a password reset token (compares hash).

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

        # Compare hashes using constant-time comparison
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return secrets.compare_digest(self.password_reset_token, token_hash)

    def clear_password_reset_token(self) -> None:
        """Clear the password reset token after use."""
        self.password_reset_token = ""
        self.password_reset_sent_at = None
        self.save(update_fields=["password_reset_token", "password_reset_sent_at"])

    def record_login_attempt(self, success: bool, ip_address: str | None = None) -> None:
        """Record a login attempt and update lockout status."""
        import structlog
        from django.core.cache import caches

        from api.audit import log_audit
        from api.tasks_lockout import check_mass_lockout_task, send_lockout_notification_task

        logger = structlog.get_logger(__name__)
        lockout_occurred = False

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
                lockout_occurred = True

        self.save(update_fields=[
            "failed_login_attempts",
            "locked_until",
            "last_login_at",
            "last_login_ip",
        ])

        # Send lockout notification if a lockout just occurred
        if lockout_occurred:
            self._send_lockout_notification(ip_address, logger)

    def _send_lockout_notification(self, ip_address: str | None, logger) -> None:
        """
        Send lockout notification email and create audit log.

        This method is called internally when a lockout occurs during record_login_attempt().
        It follows the same pattern as the django-axes signal handler.
        """
        from django.core.cache import caches

        from api.audit import log_audit
        from api.tasks_lockout import check_mass_lockout_task, send_lockout_notification_task

        logger.info(
            "local_auth_lockout_occurred",
            user_id=str(self.user.id),
            username=self.user.username,
            ip_address=ip_address,
        )

        # Calculate lockout duration (in seconds from settings)
        lockout_duration_seconds = getattr(settings, "LOCAL_AUTH_LOCKOUT_DURATION", 1800)
        lockout_duration_minutes = lockout_duration_seconds // 60
        lockout_duration_hours = lockout_duration_seconds // 3600

        # Format lockout duration for display
        if lockout_duration_hours >= 1:
            lockout_duration = f"{lockout_duration_hours} hour{'s' if lockout_duration_hours != 1 else ''}"
        else:
            lockout_duration = f"{lockout_duration_minutes} minute{'s' if lockout_duration_minutes != 1 else ''}"

        # Prepare lockout data for email
        lockout_data = {
            "lockout_duration": lockout_duration,
            "failure_count": self.failed_login_attempts,
            "ip_address": ip_address or "Unknown",
            "lockout_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "unlock_time": self.locked_until.strftime("%Y-%m-%d %H:%M:%S UTC") if self.locked_until else "Unknown",
            "reset_password_url": f"{settings.FRONTEND_URL}/reset-password" if hasattr(settings, 'FRONTEND_URL') else None,
        }

        # Prepare user data for email
        user_data = {
            "first_name": getattr(self.user, 'first_name', '') or self.user.username,
            "email": self.user.email,
            "username": self.user.username,
        }

        # Create audit log entry for the lockout
        log_audit(
            action="account_locked",
            resource_type="User",
            resource_id=str(self.user.id),
            actor_id=str(self.user.id),  # The user is the actor (attempted login)
            actor_email=self.user.email,
            metadata={
                "ip_address": ip_address or "Unknown",
                "failure_count": self.failed_login_attempts,
                "lockout_duration_seconds": lockout_duration_seconds,
                "unlock_time": self.locked_until.isoformat() if self.locked_until else None,
                "source": "local-auth",
            },
        )

        logger.info(
            "local_auth_lockout_audit_logged",
            user_id=str(self.user.id),
            username=self.user.username,
            ip_address=ip_address,
        )

        # Send notification email asynchronously (if user has email)
        if self.user.email and settings.LOCKOUT_NOTIFICATION_ENABLED:
            send_lockout_notification_task.delay(
                user_email=self.user.email,
                user_data=user_data,
                lockout_data=lockout_data,
            )
            logger.info(
                "local_auth_lockout_notification_queued",
                user_email=self.user.email,
                ip_address=ip_address,
            )
        else:
            logger.info(
                "local_auth_lockout_notification_skipped",
                username=self.user.username,
                reason="no_email" if not self.user.email else "disabled",
            )

        # Increment mass lockout counter in Redis for tracking
        cache = caches["default"]
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES
        time_window_seconds = time_window_minutes * 60
        lockout_counter_key = f"lockout_count:{time_window_minutes}m"

        try:
            # Increment counter
            current_count = cache.get(lockout_counter_key, 0)
            current_count += 1
            cache.set(lockout_counter_key, current_count, time_window_seconds)

            logger.info(
                "local_auth_mass_lockout_counter_incremented",
                count=current_count,
                threshold=settings.LOCKOUT_MASS_THRESHOLD,
                time_window_minutes=time_window_minutes,
            )

            # Check if we've crossed the mass lockout threshold
            check_mass_lockout_task.delay(current_count=current_count)

        except Exception as e:
            logger.error(
                "local_auth_mass_lockout_tracking_failed",
                error=str(e),
                username=self.user.username,
            )
            # Don't fail the whole method if tracking fails

    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False


class RefreshToken(TimeStampedModel):
    """
    Store refresh tokens for local authentication.

    Refresh tokens are stored hashed and can be revoked.
    Implements token rotation with reuse detection via family_id.
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

    # Token rotation fields for reuse detection
    family_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    generation = models.IntegerField(default=0)
    replaced_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaces",
    )

    class Meta:
        verbose_name = "Refresh Token"
        verbose_name_plural = "Refresh Tokens"
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["family_id"]),
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

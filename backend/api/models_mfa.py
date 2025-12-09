"""
TOTP Multi-Factor Authentication models.

Provides built-in TOTP MFA without requiring Keycloak MFA configuration.
"""

import hashlib
import json
import secrets
from typing import List, Optional, Tuple

import pyotp
from django.conf import settings
from django.db import models

from api.encryption import EncryptedCharField, EncryptedTextField


class TOTPDeviceManager(models.Manager):
    """Custom manager for TOTPDevice."""

    def create_device(self, user, confirmed: bool = False) -> Tuple["TOTPDevice", str]:
        """
        Create a new TOTP device for a user.

        Args:
            user: The user to create the device for
            confirmed: Whether the device is already confirmed

        Returns:
            Tuple of (device, secret_plaintext)
        """
        # Generate a new secret
        secret = pyotp.random_base32()

        # Generate initial backup codes
        backup_codes, hashed_codes = self._generate_backup_codes()

        device = self.create(
            user=user,
            secret=secret,
            confirmed=confirmed,
            backup_codes_json=json.dumps(hashed_codes),
        )

        return device, backup_codes

    def _generate_backup_codes(self, count: int = 10) -> Tuple[List[str], List[str]]:
        """
        Generate backup codes.

        Args:
            count: Number of codes to generate

        Returns:
            Tuple of (plaintext_codes, hashed_codes)
        """
        plaintext = []
        hashed = []

        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            plaintext.append(code)
            # Store hashed version
            hashed.append(hashlib.sha256(code.encode()).hexdigest())

        return plaintext, hashed


class TOTPDevice(models.Model):
    """
    TOTP device for user MFA.

    Stores encrypted TOTP secret and hashed backup codes.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret = EncryptedCharField(max_length=64)  # Base32 encoded secret
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    backup_codes_json = EncryptedTextField(blank=True, default="[]")

    objects = TOTPDeviceManager()

    class Meta:
        verbose_name = "TOTP Device"
        verbose_name_plural = "TOTP Devices"

    def __str__(self):
        status = "confirmed" if self.confirmed else "pending"
        return f"TOTP for {self.user} ({status})"

    def get_totp(self) -> pyotp.TOTP:
        """Get TOTP instance for this device."""
        return pyotp.TOTP(self.secret)

    def verify_code(self, code: str) -> bool:
        """
        Verify a TOTP code.

        Args:
            code: The 6-digit TOTP code

        Returns:
            True if code is valid
        """
        totp = self.get_totp()
        return totp.verify(code, valid_window=1)

    def verify_backup_code(self, code: str) -> bool:
        """
        Verify and consume a backup code.

        Args:
            code: The backup code to verify

        Returns:
            True if code was valid and consumed
        """
        code_hash = hashlib.sha256(code.upper().encode()).hexdigest()
        codes = json.loads(self.backup_codes_json)

        if code_hash in codes:
            codes.remove(code_hash)
            self.backup_codes_json = json.dumps(codes)
            self.save(update_fields=["backup_codes_json"])
            return True

        return False

    def get_provisioning_uri(self, issuer: Optional[str] = None) -> str:
        """
        Get the provisioning URI for QR code generation.

        Args:
            issuer: The issuer name (defaults to settings.SITE_NAME or "Django App")

        Returns:
            otpauth:// URI for QR code
        """
        if issuer is None:
            issuer = getattr(settings, "SITE_NAME", "Django App")

        totp = self.get_totp()
        return totp.provisioning_uri(
            name=self.user.email or self.user.username,
            issuer_name=issuer,
        )

    def regenerate_backup_codes(self) -> List[str]:
        """
        Regenerate backup codes (invalidates existing ones).

        Returns:
            List of new plaintext backup codes
        """
        plaintext, hashed = TOTPDevice.objects._generate_backup_codes()
        self.backup_codes_json = json.dumps(hashed)
        self.save(update_fields=["backup_codes_json"])
        return plaintext

    def remaining_backup_codes(self) -> int:
        """Return count of remaining backup codes."""
        codes = json.loads(self.backup_codes_json)
        return len(codes)


class MFAToken(models.Model):
    """
    Temporary token for MFA verification during login.

    After successful password verification but before MFA verification,
    a temporary token is issued. This token is used to complete MFA.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "MFA Token"
        verbose_name_plural = "MFA Tokens"

    def __str__(self):
        return f"MFA Token for {self.user} (expires {self.expires_at})"

    @classmethod
    def create_token(cls, user, ttl_seconds: int = 300) -> "MFAToken":
        """
        Create a new MFA token.

        Args:
            user: The user to create the token for
            ttl_seconds: Token lifetime in seconds (default 5 minutes)

        Returns:
            The created MFAToken instance
        """
        from django.utils import timezone
        import datetime

        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + datetime.timedelta(seconds=ttl_seconds)

        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
        )

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        from django.utils import timezone

        return not self.used and self.expires_at > timezone.now()

    def consume(self) -> bool:
        """
        Mark token as used.

        Returns:
            True if token was valid and consumed, False otherwise
        """
        if not self.is_valid():
            return False

        self.used = True
        self.save(update_fields=["used"])
        return True

"""
S3-style Access Key model for programmatic API access.

Provides AWS-style access_key_id + secret_access_key pairs.
The secret is encrypted at rest for HMAC signature verification.
"""

import secrets

from django.conf import settings
from django.db import models

from api.encryption import EncryptedTextField


class AccessKeyManager(models.Manager):
    """Custom manager for creating access key pairs."""

    def create_key_pair(self, user, name=""):
        """
        Create a new access key pair.

        Returns:
            tuple: (AccessKeyPair instance, secret_access_key plaintext)
        """
        # Generate access key ID (like AWS: AKIA + 16 random chars)
        access_key_id = "AK" + secrets.token_hex(8).upper()

        # Generate secret access key (40 chars, URL-safe)
        secret_access_key = secrets.token_urlsafe(30)

        key_pair = self.create(
            user=user,
            name=name or f"Access Key {self.filter(user=user).count() + 1}",
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,  # Encrypted at rest
        )

        return key_pair, secret_access_key


class AccessKeyPair(models.Model):
    """
    S3-style access key pair for API authentication.

    Similar to AWS access keys: a public access_key_id and a secret
    that's only shown once at creation time.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_keys",
    )
    name = models.CharField(max_length=100, blank=True)
    access_key_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
    )
    # Encrypted at rest - needed for HMAC signature verification
    secret_access_key = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)

    objects = AccessKeyManager()

    class Meta:
        verbose_name = "Access key pair"
        verbose_name_plural = "Access key pairs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.access_key_id} ({self.user.email})"

    def update_last_used(self):
        """Update the last_used_at timestamp."""
        from django.utils import timezone

        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    def revoke(self):
        """Revoke this access key."""
        self.revoked = True
        self.save(update_fields=["revoked"])

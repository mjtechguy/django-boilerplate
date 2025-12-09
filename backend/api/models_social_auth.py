"""
Models for Social OAuth authentication.

Stores social account connections for users.
"""

from django.conf import settings
from django.db import models


class SocialAccount(models.Model):
    """
    Links a user to their social provider account.

    Allows a user to have multiple social accounts connected
    (e.g., both Google and GitHub).
    """

    PROVIDER_CHOICES = [
        ("google", "Google"),
        ("github", "GitHub"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Social Account"
        verbose_name_plural = "Social Accounts"
        unique_together = [("provider", "provider_id")]
        indexes = [
            models.Index(fields=["provider", "provider_id"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.provider}"

"""
Site settings model for global configuration.

Stores site-wide settings like name, logo, and favicon that can be
configured via the admin UI.
"""

import uuid

from django.db import models
from django.utils import timezone


class SiteSettings(models.Model):
    """
    Singleton model for site-wide settings.

    Only one instance should exist. Use get_settings() to retrieve it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Branding
    site_name = models.CharField(
        max_length=255,
        default="Platform",
        help_text="The name displayed in the browser tab and header",
    )
    logo_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL to the site logo image",
    )
    favicon_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL to the favicon",
    )

    # Optional additional branding
    primary_color = models.CharField(
        max_length=7,
        default="#10b981",
        help_text="Primary brand color (hex format, e.g., #10b981)",
    )
    support_email = models.EmailField(
        blank=True,
        default="",
        help_text="Support email address displayed to users",
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self) -> str:
        return f"Site Settings ({self.site_name})"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        if not self.pk and SiteSettings.objects.exists():
            # Update the existing instance instead
            existing = SiteSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls) -> "SiteSettings":
        """
        Get or create the singleton settings instance.

        Returns:
            The SiteSettings instance
        """
        settings, _ = cls.objects.get_or_create(
            defaults={
                "site_name": "Platform",
                "primary_color": "#10b981",
            }
        )
        return settings

from django.conf import settings
from django.db import models
from rest_framework_api_key.models import AbstractAPIKey


class UserAPIKey(AbstractAPIKey):
    """
    API Key associated with a User, allowing scoped API access based on user permissions.

    Keys are hashed at rest using the rest_framework_api_key library.
    The plaintext key is only shown once at creation time.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys"
    )

    class Meta(AbstractAPIKey.Meta):
        verbose_name = "User API key"
        verbose_name_plural = "User API keys"

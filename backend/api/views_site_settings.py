"""
Site settings API views.

Provides endpoints to get and update site-wide settings.
"""

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models_site_settings import SiteSettings
from api.permissions import IsPlatformAdmin


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Serializer for site settings."""

    class Meta:
        model = SiteSettings
        fields = [
            "site_name",
            "logo_url",
            "favicon_url",
            "primary_color",
            "support_email",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class SiteSettingsPublicSerializer(serializers.ModelSerializer):
    """
    Public serializer for site settings.

    Exposes only the fields needed for branding the frontend.
    """

    class Meta:
        model = SiteSettings
        fields = [
            "site_name",
            "logo_url",
            "favicon_url",
            "primary_color",
        ]


class SiteSettingsView(APIView):
    """
    Get site settings (public).

    GET /api/v1/settings/site
    Returns the site branding settings. This endpoint is public
    so the frontend can display the correct branding before login.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsPublicSerializer(settings)
        return Response(serializer.data)


class SiteSettingsAdminView(APIView):
    """
    Get and update site settings (admin only).

    GET /api/v1/admin/settings/site
    Returns all site settings fields.

    PUT /api/v1/admin/settings/site
    Updates site settings. Requires admin privileges.
    """

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        """Alias for PUT with partial update."""
        return self.put(request)

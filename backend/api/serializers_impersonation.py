"""
Serializers for impersonation log endpoints.
"""

from rest_framework import serializers

from api.models import ImpersonationLog


class ImpersonationLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for ImpersonationLog."""

    class Meta:
        model = ImpersonationLog
        fields = [
            "id",
            "admin_id",
            "admin_email",
            "target_user_id",
            "target_user_email",
            "org_id",
            "action",
            "endpoint",
            "method",
            "request_id",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

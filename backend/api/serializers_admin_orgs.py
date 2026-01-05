"""
Serializers for admin org management endpoints.

Provides serializers for Org CRUD operations.
"""

from rest_framework import serializers

from api.models import Org


class OrgSerializer(serializers.ModelSerializer):
    """Serializer for Org model - read operations."""

    teams_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Org
        fields = [
            "id",
            "name",
            "status",
            "license_tier",
            "feature_flags",
            "teams_count",
            "members_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "teams_count", "members_count"]

    def get_teams_count(self, obj) -> int:
        """Return count of teams in this org."""
        return obj.teams.count()

    def get_members_count(self, obj) -> int:
        """Return count of unique members in this org."""
        return obj.memberships.values("user_id").distinct().count()


class OrgCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Org."""

    class Meta:
        model = Org
        fields = [
            "id",
            "name",
            "status",
            "license_tier",
            "feature_flags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        """Validate org name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Organization name cannot be empty.")
        return value.strip()


class OrgUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an Org."""

    class Meta:
        model = Org
        fields = [
            "name",
            "status",
            "license_tier",
            "feature_flags",
        ]

    def validate_name(self, value: str) -> str:
        """Validate org name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Organization name cannot be empty.")
        return value.strip()

    def validate_status(self, value: str) -> str:
        """Validate status is a valid choice."""
        valid_statuses = [choice[0] for choice in Org.Status.choices]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value


class OrgListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Org list view."""

    teams_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Org
        fields = [
            "id",
            "name",
            "status",
            "license_tier",
            "teams_count",
            "members_count",
            "created_at",
        ]

    def get_teams_count(self, obj) -> int:
        """Return count of teams in this org."""
        # Use prefetched data if available
        if hasattr(obj, "_teams_count"):
            return obj._teams_count
        return obj.teams.count()

    def get_members_count(self, obj) -> int:
        """Return count of unique members in this org."""
        if hasattr(obj, "_members_count"):
            return obj._members_count
        return obj.memberships.values("user_id").distinct().count()

"""
Serializers for admin division management endpoints.

Provides serializers for Division CRUD operations.
"""

from rest_framework import serializers

from api.models import Division


class DivisionSerializer(serializers.ModelSerializer):
    """Read serializer for Division with computed fields."""

    org_name = serializers.CharField(source="org.name", read_only=True)
    teams_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Division
        fields = [
            "id",
            "org",
            "org_name",
            "name",
            "billing_mode",
            "license_tier",
            "feature_flags",
            "stripe_customer_id",
            "stripe_subscription_id",
            "billing_email",
            "teams_count",
            "members_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_teams_count(self, obj) -> int:
        """Return count of teams in this division."""
        return obj.teams.count()

    def get_members_count(self, obj) -> int:
        """Return count of members in this division."""
        return obj.memberships.count()


class DivisionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Division list view."""

    org_name = serializers.CharField(source="org.name", read_only=True)
    teams_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Division
        fields = [
            "id",
            "org",
            "org_name",
            "name",
            "billing_mode",
            "license_tier",
            "teams_count",
            "members_count",
            "created_at",
        ]

    def get_teams_count(self, obj) -> int:
        """Return count of teams in this division."""
        if hasattr(obj, "_teams_count"):
            return obj._teams_count
        return obj.teams.count()

    def get_members_count(self, obj) -> int:
        """Return count of members in this division."""
        if hasattr(obj, "_members_count"):
            return obj._members_count
        return obj.memberships.count()


class DivisionCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Division."""

    class Meta:
        model = Division
        fields = [
            "id",
            "org",
            "name",
            "billing_mode",
            "license_tier",
            "feature_flags",
            "billing_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        """Validate division name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Division name cannot be empty.")
        return value.strip()

    def validate(self, attrs):
        """Validate division constraints."""
        org = attrs.get("org")
        name = attrs.get("name")

        # Check for unique name within org
        if org and name:
            if Division.objects.filter(org=org, name=name).exists():
                raise serializers.ValidationError(
                    {"name": "A division with this name already exists in this organization."}
                )

        # If billing_mode is independent, license_tier should be set
        if attrs.get("billing_mode") == "independent" and not attrs.get("license_tier"):
            attrs["license_tier"] = "free"  # Default to free if not specified

        return attrs


class DivisionUpdateSerializer(serializers.ModelSerializer):
    """Update serializer for Division."""

    class Meta:
        model = Division
        fields = [
            "name",
            "billing_mode",
            "license_tier",
            "feature_flags",
            "billing_email",
        ]

    def validate_name(self, value: str) -> str:
        """Validate division name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Division name cannot be empty.")
        return value.strip()

    def validate(self, attrs):
        """Validate division constraints."""
        # Validate name uniqueness within org
        if self.instance and "name" in attrs:
            name = attrs["name"]
            org = self.instance.org
            if Division.objects.filter(org=org, name=name).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    {"name": "A division with this name already exists in this organization."}
                )

        # Ensure license_tier is set when switching to independent billing
        if attrs.get("billing_mode") == "independent":
            if not attrs.get("license_tier") and not (
                self.instance and self.instance.license_tier
            ):
                attrs["license_tier"] = "free"

        return attrs

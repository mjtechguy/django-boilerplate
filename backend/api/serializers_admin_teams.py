"""
Serializers for admin team management endpoints.

Provides serializers for Team CRUD operations.
"""

from rest_framework import serializers

from api.models import Team


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for Team model - detail view."""

    org_name = serializers.CharField(source="org.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True, allow_null=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "org",
            "org_name",
            "division",
            "division_name",
            "members_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "org_name", "division_name", "members_count"]

    def get_members_count(self, obj) -> int:
        """Return count of members in this team."""
        return obj.memberships.count()


class TeamListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Team list view."""

    org_name = serializers.CharField(source="org.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True, allow_null=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "org",
            "org_name",
            "division",
            "division_name",
            "members_count",
            "created_at",
        ]

    def get_members_count(self, obj) -> int:
        """Return count of members in this team."""
        if hasattr(obj, "_members_count"):
            return obj._members_count
        return obj.memberships.count()


class TeamCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Team."""

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "org",
            "division",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        """Validate team name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Team name cannot be empty.")
        return value.strip()

    def validate(self, data):
        """Validate team constraints."""
        org = data.get("org")
        division = data.get("division")
        name = data.get("name")

        # If division is specified, ensure it belongs to the org
        if division and division.org_id != org.id:
            raise serializers.ValidationError(
                {"division": "Division must belong to the specified organization."}
            )

        # Check for unique name within org and division
        if org and name:
            if Team.objects.filter(org=org, division=division, name=name).exists():
                raise serializers.ValidationError(
                    {"name": "A team with this name already exists in this organization/division."}
                )
        return data


class TeamUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a Team."""

    class Meta:
        model = Team
        fields = ["name", "division"]

    def validate_name(self, value: str) -> str:
        """Validate team name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Team name cannot be empty.")
        return value.strip()

    def validate_division(self, value):
        """Validate division belongs to the team's org."""
        if value and self.instance:
            if value.org_id != self.instance.org_id:
                raise serializers.ValidationError(
                    "Division must belong to the team's organization."
                )
        return value

    def validate(self, data):
        """Validate team constraints."""
        if self.instance and "name" in data:
            name = data["name"]
            org = self.instance.org
            division = data.get("division", self.instance.division)
            if Team.objects.filter(org=org, division=division, name=name).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    {"name": "A team with this name already exists in this organization/division."}
                )
        return data

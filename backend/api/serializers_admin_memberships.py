"""
Serializers for admin membership management endpoints.

Provides serializers for Membership CRUD operations.
"""

from rest_framework import serializers

from api.models import Membership


class MembershipSerializer(serializers.ModelSerializer):
    """Serializer for Membership model - detail view."""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    org_name = serializers.CharField(source="org.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True, allow_null=True)
    team_name = serializers.CharField(source="team.name", read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "org",
            "org_name",
            "division",
            "division_name",
            "team",
            "team_name",
            "org_roles",
            "division_roles",
            "team_roles",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user_email", "user_name", "org_name", "division_name", "team_name"]

    def get_user_name(self, obj) -> str:
        """Get user full name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class MembershipListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Membership list view."""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    org_name = serializers.CharField(source="org.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True, allow_null=True)
    team_name = serializers.CharField(source="team.name", read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "org",
            "org_name",
            "division",
            "division_name",
            "team",
            "team_name",
            "org_roles",
            "division_roles",
            "team_roles",
            "created_at",
        ]

    def get_user_name(self, obj) -> str:
        """Get user full name."""
        if hasattr(obj, "_user_name"):
            return obj._user_name
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class MembershipCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Membership."""

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "org",
            "division",
            "team",
            "org_roles",
            "division_roles",
            "team_roles",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        """Validate membership constraints."""
        user = data.get("user")
        org = data.get("org")
        division = data.get("division")
        team = data.get("team")

        # Check if membership already exists
        existing = Membership.objects.filter(user=user, org=org, team=team)
        if existing.exists():
            raise serializers.ValidationError(
                {"non_field_errors": "This membership already exists."}
            )

        # If division is specified, ensure it belongs to the org
        if division and division.org_id != org.id:
            raise serializers.ValidationError(
                {"division": "Division must belong to the specified organization."}
            )

        # If team is specified, ensure it belongs to the org
        if team and team.org_id != org.id:
            raise serializers.ValidationError(
                {"team": "Team must belong to the specified organization."}
            )

        return data


class MembershipUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a Membership."""

    class Meta:
        model = Membership
        fields = ["org_roles", "division_roles", "team_roles", "division", "team"]

    def validate_division(self, value):
        """Validate division belongs to the membership's org."""
        if value and self.instance:
            if value.org_id != self.instance.org_id:
                raise serializers.ValidationError(
                    "Division must belong to the membership's organization."
                )
        return value

    def validate_team(self, value):
        """Validate team belongs to the membership's org."""
        if value and self.instance:
            if value.org_id != self.instance.org_id:
                raise serializers.ValidationError(
                    "Team must belong to the membership's organization."
                )
        return value

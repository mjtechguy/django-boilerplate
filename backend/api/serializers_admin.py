"""
Serializers for admin management endpoints.

Provides serializers for Org, Team, User, and Membership CRUD operations.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.models import Division, Membership, Org, Team
from api.models_local_auth import LocalUserProfile

User = get_user_model()


class NameValidationMixin:
    """Mixin for validating name fields in serializers.

    Provides a validate_name method that checks for empty/whitespace-only values
    and returns the stripped value. Error messages can be customized via the
    name_entity_type class attribute.
    """

    name_entity_type = "Name"

    def validate_name(self, value: str) -> str:
        """Validate name is not empty and return stripped value.

        Args:
            value: The name value to validate

        Returns:
            The stripped name value

        Raises:
            ValidationError: If name is empty or whitespace-only
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                f"{self.name_entity_type} name cannot be empty."
            )
        return value.strip()


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


class OrgCreateSerializer(NameValidationMixin, serializers.ModelSerializer):
    """Serializer for creating a new Org."""

    name_entity_type = "Organization"

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


class OrgUpdateSerializer(NameValidationMixin, serializers.ModelSerializer):
    """Serializer for updating an Org."""

    name_entity_type = "Organization"

    class Meta:
        model = Org
        fields = [
            "name",
            "status",
            "license_tier",
            "feature_flags",
        ]

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


# =============================================================================
# Division Serializers
# =============================================================================


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


class DivisionCreateSerializer(NameValidationMixin, serializers.ModelSerializer):
    """Create serializer for Division."""

    name_entity_type = "Division"

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


# =============================================================================
# Team Serializers
# =============================================================================


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


# =============================================================================
# User Serializers
# =============================================================================


class UserMembershipSerializer(serializers.ModelSerializer):
    """Serializer for user memberships in detail view."""

    org_name = serializers.CharField(source="org.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True, allow_null=True)
    team_name = serializers.CharField(source="team.name", read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = [
            "id",
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


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - detail view."""

    auth_provider = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    memberships_count = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "auth_provider",
            "email_verified",
            "roles",
            "memberships_count",
            "memberships",
            "date_joined",
            "last_login",
        ]

    def get_auth_provider(self, obj) -> str:
        """Get auth provider from local profile or default to oidc."""
        if hasattr(obj, "local_profile"):
            return obj.local_profile.auth_provider
        return "oidc"

    def get_email_verified(self, obj) -> bool:
        """Get email verification status."""
        if hasattr(obj, "local_profile"):
            return obj.local_profile.email_verified
        return True  # OIDC users are assumed verified

    def get_roles(self, obj) -> list:
        """Get user roles from local profile."""
        if hasattr(obj, "local_profile"):
            return obj.local_profile.roles
        return []

    def get_memberships_count(self, obj) -> int:
        """Return count of memberships."""
        return obj.memberships.count()

    def get_memberships(self, obj) -> list:
        """Get user memberships."""
        memberships = obj.memberships.select_related("org", "team").all()
        return UserMembershipSerializer(memberships, many=True).data


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for User list view."""

    auth_provider = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    memberships_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "auth_provider",
            "email_verified",
            "roles",
            "memberships_count",
            "date_joined",
        ]

    def get_auth_provider(self, obj) -> str:
        """Get auth provider from local profile or default to oidc."""
        if hasattr(obj, "_auth_provider"):
            return obj._auth_provider
        if hasattr(obj, "local_profile"):
            return obj.local_profile.auth_provider
        return "oidc"

    def get_email_verified(self, obj) -> bool:
        """Get email verification status."""
        if hasattr(obj, "_email_verified"):
            return obj._email_verified
        if hasattr(obj, "local_profile"):
            return obj.local_profile.email_verified
        return True

    def get_roles(self, obj) -> list:
        """Get user roles from local profile."""
        if hasattr(obj, "_roles"):
            return obj._roles
        if hasattr(obj, "local_profile"):
            return obj.local_profile.roles
        return []

    def get_memberships_count(self, obj) -> int:
        """Return count of memberships."""
        if hasattr(obj, "_memberships_count"):
            return obj._memberships_count
        return obj.memberships.count()


class UserCreateSerializer(serializers.Serializer):
    """Serializer for creating a new local user."""

    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    roles = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        default=list,
    )

    def validate_email(self, value: str) -> str:
        """Validate email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value: str) -> str:
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        return value

    def create(self, validated_data):
        """Create local user with password."""
        roles = validated_data.pop("roles", [])
        password = validated_data.pop("password")

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )

        # Create local profile
        profile = LocalUserProfile.objects.create(
            user=user,
            auth_provider="local",
            email_verified=True,  # Admin-created users are pre-verified
            roles=roles,
        )
        profile.set_password(password)
        profile.save()

        return user


class UserInviteSerializer(serializers.Serializer):
    """Serializer for inviting an OIDC user."""

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    roles = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        default=list,
    )
    org_id = serializers.UUIDField(required=False, allow_null=True)
    org_roles = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        default=list,
    )

    def validate_email(self, value: str) -> str:
        """Validate email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_org_id(self, value):
        """Validate org exists if provided."""
        if value:
            if not Org.objects.filter(id=value).exists():
                raise serializers.ValidationError("Organization not found.")
        return value

    def create(self, validated_data):
        """Create pre-provisioned OIDC user."""
        roles = validated_data.pop("roles", [])
        org_id = validated_data.pop("org_id", None)
        org_roles = validated_data.pop("org_roles", [])

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_active=True,
        )

        # Create local profile with OIDC provider (no password)
        LocalUserProfile.objects.create(
            user=user,
            auth_provider="oidc",
            email_verified=False,  # Will be verified on first SSO login
            roles=roles,
            password_hash="",  # No password for OIDC users
        )

        # Create org membership if org provided
        if org_id:
            Membership.objects.create(
                user=user,
                org_id=org_id,
                org_roles=org_roles or ["user"],
            )

        return user


class UserUpdateSerializer(serializers.Serializer):
    """Serializer for updating a user."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    is_active = serializers.BooleanField(required=False)
    roles = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
    )

    def update(self, instance, validated_data):
        """Update user fields."""
        roles = validated_data.pop("roles", None)

        # Update User fields
        if "first_name" in validated_data:
            instance.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            instance.last_name = validated_data["last_name"]
        if "is_active" in validated_data:
            instance.is_active = validated_data["is_active"]
        instance.save()

        # Update roles in local profile
        if roles is not None and hasattr(instance, "local_profile"):
            instance.local_profile.roles = roles
            instance.local_profile.save(update_fields=["roles"])

        return instance


# =============================================================================
# Membership Serializers
# =============================================================================


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

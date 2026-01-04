"""
Serializers for admin user management endpoints.

Provides serializers for User CRUD operations.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.models import Membership, Org
from api.models_local_auth import LocalUserProfile

User = get_user_model()


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

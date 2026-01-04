"""
Tests for serializer mixins.

This module tests the NameValidationMixin used by various serializers.
"""

import pytest
from rest_framework import serializers

from api.models import Division, Org, Team
from api.serializers_admin import (
    DivisionCreateSerializer,
    DivisionUpdateSerializer,
    NameValidationMixin,
    OrgCreateSerializer,
    OrgUpdateSerializer,
    TeamCreateSerializer,
    TeamUpdateSerializer,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# NameValidationMixin Direct Tests
# =============================================================================


class TestNameValidationMixin:
    """Test the NameValidationMixin directly."""

    def test_validate_name_with_empty_string_raises_error(self):
        """Test that empty string raises ValidationError."""

        class TestSerializer(NameValidationMixin, serializers.Serializer):
            name = serializers.CharField()

        serializer = TestSerializer(data={"name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Name name cannot be empty." in str(serializer.errors["name"])

    def test_validate_name_with_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ValidationError."""

        class TestSerializer(NameValidationMixin, serializers.Serializer):
            name = serializers.CharField()

        test_cases = ["   ", "\t", "\n", "  \t\n  "]
        for whitespace in test_cases:
            serializer = TestSerializer(data={"name": whitespace})
            assert not serializer.is_valid()
            assert "name" in serializer.errors
            assert "Name name cannot be empty." in str(serializer.errors["name"])

    def test_validate_name_with_valid_string_strips_whitespace(self):
        """Test that valid string is stripped of leading/trailing whitespace."""

        class TestSerializer(NameValidationMixin, serializers.Serializer):
            name = serializers.CharField()

            class Meta:
                fields = ["name"]

        # Test with leading whitespace
        serializer = TestSerializer(data={"name": "  Valid Name"})
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Valid Name"

        # Test with trailing whitespace
        serializer = TestSerializer(data={"name": "Valid Name  "})
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Valid Name"

        # Test with both
        serializer = TestSerializer(data={"name": "  Valid Name  "})
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Valid Name"

    def test_validate_name_with_custom_entity_type_in_error_message(self):
        """Test that custom entity type is used in error messages."""

        class CustomEntitySerializer(NameValidationMixin, serializers.Serializer):
            name = serializers.CharField()
            name_entity_type = "CustomEntity"

        serializer = CustomEntitySerializer(data={"name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "CustomEntity name cannot be empty." in str(serializer.errors["name"])

    def test_validate_name_default_entity_type(self):
        """Test that default entity type is 'Name'."""

        class DefaultSerializer(NameValidationMixin, serializers.Serializer):
            name = serializers.CharField()

        serializer = DefaultSerializer(data={"name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Name name cannot be empty." in str(serializer.errors["name"])


# =============================================================================
# OrgCreateSerializer Tests
# =============================================================================


class TestOrgCreateSerializer:
    """Test OrgCreateSerializer uses NameValidationMixin correctly."""

    def test_org_create_with_empty_name_fails(self):
        """Test that creating org with empty name fails."""
        serializer = OrgCreateSerializer(data={"name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Organization name cannot be empty." in str(serializer.errors["name"])

    def test_org_create_with_whitespace_only_name_fails(self):
        """Test that creating org with whitespace-only name fails."""
        serializer = OrgCreateSerializer(data={"name": "   "})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Organization name cannot be empty." in str(serializer.errors["name"])

    def test_org_create_with_valid_name_strips_whitespace(self):
        """Test that creating org with valid name strips whitespace."""
        serializer = OrgCreateSerializer(data={"name": "  Acme Corp  "})
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Acme Corp"

    def test_org_create_saves_with_stripped_name(self):
        """Test that org is created with stripped name."""
        serializer = OrgCreateSerializer(data={"name": "  Acme Corp  "})
        assert serializer.is_valid()
        org = serializer.save()
        assert org.name == "Acme Corp"


# =============================================================================
# OrgUpdateSerializer Tests
# =============================================================================


class TestOrgUpdateSerializer:
    """Test OrgUpdateSerializer uses NameValidationMixin correctly."""

    def test_org_update_with_empty_name_fails(self):
        """Test that updating org with empty name fails."""
        org = Org.objects.create(name="Original Name")
        serializer = OrgUpdateSerializer(org, data={"name": ""}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Organization name cannot be empty." in str(serializer.errors["name"])

    def test_org_update_with_whitespace_only_name_fails(self):
        """Test that updating org with whitespace-only name fails."""
        org = Org.objects.create(name="Original Name")
        serializer = OrgUpdateSerializer(org, data={"name": "   "}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Organization name cannot be empty." in str(serializer.errors["name"])

    def test_org_update_with_valid_name_strips_whitespace(self):
        """Test that updating org with valid name strips whitespace."""
        org = Org.objects.create(name="Original Name")
        serializer = OrgUpdateSerializer(org, data={"name": "  New Name  "}, partial=True)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "New Name"


# =============================================================================
# DivisionCreateSerializer Tests
# =============================================================================


class TestDivisionCreateSerializer:
    """Test DivisionCreateSerializer uses NameValidationMixin correctly."""

    def test_division_create_with_empty_name_fails(self):
        """Test that creating division with empty name fails."""
        org = Org.objects.create(name="Acme Corp")
        serializer = DivisionCreateSerializer(data={"org": org.id, "name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Division name cannot be empty." in str(serializer.errors["name"])

    def test_division_create_with_whitespace_only_name_fails(self):
        """Test that creating division with whitespace-only name fails."""
        org = Org.objects.create(name="Acme Corp")
        serializer = DivisionCreateSerializer(data={"org": org.id, "name": "   "})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Division name cannot be empty." in str(serializer.errors["name"])

    def test_division_create_with_valid_name_strips_whitespace(self):
        """Test that creating division with valid name strips whitespace."""
        org = Org.objects.create(name="Acme Corp")
        serializer = DivisionCreateSerializer(data={"org": org.id, "name": "  Engineering  "})
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Engineering"

    def test_division_create_saves_with_stripped_name(self):
        """Test that division is created with stripped name."""
        org = Org.objects.create(name="Acme Corp")
        serializer = DivisionCreateSerializer(data={"org": org.id, "name": "  Engineering  "})
        assert serializer.is_valid()
        division = serializer.save()
        assert division.name == "Engineering"


# =============================================================================
# DivisionUpdateSerializer Tests
# =============================================================================


class TestDivisionUpdateSerializer:
    """Test DivisionUpdateSerializer uses NameValidationMixin correctly."""

    def test_division_update_with_empty_name_fails(self):
        """Test that updating division with empty name fails."""
        org = Org.objects.create(name="Acme Corp")
        division = Division.objects.create(org=org, name="Original Name")
        serializer = DivisionUpdateSerializer(division, data={"name": ""}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Division name cannot be empty." in str(serializer.errors["name"])

    def test_division_update_with_whitespace_only_name_fails(self):
        """Test that updating division with whitespace-only name fails."""
        org = Org.objects.create(name="Acme Corp")
        division = Division.objects.create(org=org, name="Original Name")
        serializer = DivisionUpdateSerializer(division, data={"name": "   "}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Division name cannot be empty." in str(serializer.errors["name"])

    def test_division_update_with_valid_name_strips_whitespace(self):
        """Test that updating division with valid name strips whitespace."""
        org = Org.objects.create(name="Acme Corp")
        division = Division.objects.create(org=org, name="Original Name")
        serializer = DivisionUpdateSerializer(division, data={"name": "  New Name  "}, partial=True)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "New Name"


# =============================================================================
# TeamCreateSerializer Tests
# =============================================================================


class TestTeamCreateSerializer:
    """Test TeamCreateSerializer uses NameValidationMixin correctly."""

    def test_team_create_with_empty_name_fails(self):
        """Test that creating team with empty name fails."""
        org = Org.objects.create(name="Acme Corp")
        serializer = TeamCreateSerializer(data={"org": org.id, "name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Team name cannot be empty." in str(serializer.errors["name"])

    def test_team_create_with_whitespace_only_name_fails(self):
        """Test that creating team with whitespace-only name fails."""
        org = Org.objects.create(name="Acme Corp")
        serializer = TeamCreateSerializer(data={"org": org.id, "name": "   "})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Team name cannot be empty." in str(serializer.errors["name"])

    def test_team_create_with_valid_name_strips_whitespace(self):
        """Test that creating team with valid name strips whitespace."""
        org = Org.objects.create(name="Acme Corp")
        serializer = TeamCreateSerializer(data={"org": org.id, "name": "  Backend Team  "})
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Backend Team"

    def test_team_create_saves_with_stripped_name(self):
        """Test that team is created with stripped name."""
        org = Org.objects.create(name="Acme Corp")
        serializer = TeamCreateSerializer(data={"org": org.id, "name": "  Backend Team  "})
        assert serializer.is_valid()
        team = serializer.save()
        assert team.name == "Backend Team"


# =============================================================================
# TeamUpdateSerializer Tests
# =============================================================================


class TestTeamUpdateSerializer:
    """Test TeamUpdateSerializer uses NameValidationMixin correctly."""

    def test_team_update_with_empty_name_fails(self):
        """Test that updating team with empty name fails."""
        org = Org.objects.create(name="Acme Corp")
        team = Team.objects.create(org=org, name="Original Name")
        serializer = TeamUpdateSerializer(team, data={"name": ""}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Team name cannot be empty." in str(serializer.errors["name"])

    def test_team_update_with_whitespace_only_name_fails(self):
        """Test that updating team with whitespace-only name fails."""
        org = Org.objects.create(name="Acme Corp")
        team = Team.objects.create(org=org, name="Original Name")
        serializer = TeamUpdateSerializer(team, data={"name": "   "}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "Team name cannot be empty." in str(serializer.errors["name"])

    def test_team_update_with_valid_name_strips_whitespace(self):
        """Test that updating team with valid name strips whitespace."""
        org = Org.objects.create(name="Acme Corp")
        team = Team.objects.create(org=org, name="Original Name")
        serializer = TeamUpdateSerializer(team, data={"name": "  New Name  "}, partial=True)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "New Name"

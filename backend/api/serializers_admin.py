"""
Serializers for admin management endpoints.

This module provides backward compatibility by re-exporting all serializers
from the domain-specific modules. For new code, prefer importing directly from
the specific modules:

- api.serializers_admin_orgs - Organization serializers
- api.serializers_admin_divisions - Division serializers
- api.serializers_admin_teams - Team serializers
- api.serializers_admin_users - User serializers
- api.serializers_admin_memberships - Membership serializers
"""

# Organization serializers
from api.serializers_admin_orgs import (
    OrgCreateSerializer,
    OrgListSerializer,
    OrgSerializer,
    OrgUpdateSerializer,
)

# Division serializers
from api.serializers_admin_divisions import (
    DivisionCreateSerializer,
    DivisionListSerializer,
    DivisionSerializer,
    DivisionUpdateSerializer,
)

# Team serializers
from api.serializers_admin_teams import (
    TeamCreateSerializer,
    TeamListSerializer,
    TeamSerializer,
    TeamUpdateSerializer,
)

# User serializers
from api.serializers_admin_users import (
    UserCreateSerializer,
    UserInviteSerializer,
    UserListSerializer,
    UserMembershipSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

# Membership serializers
from api.serializers_admin_memberships import (
    MembershipCreateSerializer,
    MembershipListSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
)

__all__ = [
    # Organization serializers
    "OrgSerializer",
    "OrgCreateSerializer",
    "OrgUpdateSerializer",
    "OrgListSerializer",
    # Division serializers
    "DivisionSerializer",
    "DivisionListSerializer",
    "DivisionCreateSerializer",
    "DivisionUpdateSerializer",
    # Team serializers
    "TeamSerializer",
    "TeamListSerializer",
    "TeamCreateSerializer",
    "TeamUpdateSerializer",
    # User serializers
    "UserMembershipSerializer",
    "UserSerializer",
    "UserListSerializer",
    "UserCreateSerializer",
    "UserInviteSerializer",
    "UserUpdateSerializer",
    # Membership serializers
    "MembershipSerializer",
    "MembershipListSerializer",
    "MembershipCreateSerializer",
    "MembershipUpdateSerializer",
]

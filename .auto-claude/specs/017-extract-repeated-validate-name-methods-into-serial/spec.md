# Extract Repeated validate_name Methods into Serializer Mixin

## Overview

The serializers_admin.py file contains 6 nearly identical validate_name methods across OrgCreateSerializer, OrgUpdateSerializer, DivisionCreateSerializer, DivisionUpdateSerializer, TeamCreateSerializer, and TeamUpdateSerializer. Each validates that the name field is not empty with identical logic.

## Rationale

Duplicated validation logic increases maintenance burden and risks inconsistent behavior when changes are needed. A single mixin would ensure consistent validation across all serializers.

---
*This spec was created from ideation and is pending detailed specification.*

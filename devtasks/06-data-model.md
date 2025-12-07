# Plan 06: Data Model (AuthZ-Relevant)

## Tasks
- Create models/migrations: User (shadow via default User with Keycloak sub), Org, Team, Membership (org_roles, team_roles), Settings (scoped key/value), Resource base mixin (org_id, team_id, sensitivity/pii flags). ✅ (`api/models.py`, migration 0001)
- Add fields on Org/Settings for license_tier, feature_flags. ✅
- Add indexes for org_id/team_id lookups; constraints to enforce tenant isolation. ✅
- Seed fixtures for sample org/team/membership. ☐ (optional sample data)

## Tests / Validation
- Migrations apply cleanly. ✅ (`python manage.py migrate` under test settings)
- Unit tests: model constraints, membership role serialization, settings precedence helper (env default vs global vs org). ✅ (basic precedence and uniqueness checks added)
- Basic RLS-like checks in code (queries filtered by org_id). ✅ (OrgScopedQuerySet.for_org tested)

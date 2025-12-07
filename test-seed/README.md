# Test Seed Instructions

This seeds Keycloak and Django with test users/orgs and fetches tokens for exercising APIs.

## Prereqs
- `docker compose -f compose/docker-compose.yml up --build`
- `docker compose exec web python manage.py migrate`
- Keycloak admin creds (default in compose): `admin` / `admin`
- If you change `keycloak/realm-app.json` (e.g., scopes), restart Keycloak so it re-imports the realm or delete the `keycloak` volume before `up`.

## Seed data
1) Seed Django data (orgs/teams/resources/settings):
```bash
docker compose exec web python manage.py shell < test-seed/seed.py
```

2) Seed Keycloak test users/roles:
```bash
python test-seed/keycloak_seed.py
```

3) Fetch tokens for all test users:
```bash
python test-seed/keycloak_tokens.py
```

Tokens are printed for:
- `platform_admin`
- `org_admin`
- `org_member`
- `team_admin`
- `end_user`

## What to test (Bearer JWTs; no cookies)
- `/api/v1/ping` with any valid token → 200
- `/api/v1/protected`:
  - platform_admin/org_admin/team_admin (matching org) → 200
  - org_member/end_user → 403
- `/api/v1/orgs/<org_id>/license`:
  - org_admin/platform_admin with matching org → 200
  - org_member/end_user → 403
- `/api/v1/admin/orgs`:
  - platform_admin → 200
  - org_admin/org_member/end_user → 403

## Notes
- Auth uses Bearer JWT (Authorization header) with full JWT from Keycloak.
- Cerbos policies mounted from `policies/`; protected endpoint uses `sample_resource` policy.

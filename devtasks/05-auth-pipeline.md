# Plan 05: Auth Pipeline (DRF)

## Versions / Dependencies
- DRF auth class (custom), python-keycloak, structlog, Redis (for idempotency cache).

## Tasks
- Implement DRF authentication class to validate JWT (issuer/audience/exp/sig) for each audience; extract realm + client roles, org/tenant claims, MFA flags. ✅ (`api/auth.py`)
- Map token to shadow User (Keycloak sub), create if missing. ✅
- Add idempotency middleware for mutating endpoints (Redis-backed). ✅ (`api/idempotency.py`)
- Enforce API version prefix `/api/v1`. ✅
- Add sample auth-protected endpoint to verify principal mapping. ✅ (`api/views.py` ping)

## Tests / Validation
- Unit/Integration: token validation bypass via monkeypatch, auth ping with valid token passes, missing token 401, idempotency key blocks duplicates. ✅ (pytest suite)
- Lint/tests in CI. ☐ (CI wired; tests now present)

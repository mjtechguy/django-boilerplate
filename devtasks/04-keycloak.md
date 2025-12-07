# Plan 04: Keycloak Integration

## Versions / Dependencies
- Keycloak container (matching stable LTS), python-keycloak==5.8.1.

## Tasks
- Prepare realm import JSON: clients for global-admin, org-admin, end-user with correct audiences/redirects; seed roles (realm + client). ✅ (`keycloak/realm-app.json`)
- Configure Keycloak in Compose with realm import volume; expose admin UI locally. ✅
- Add helper script using python-keycloak for JWKS retrieval/cache and basic admin ops (optional). ✅ (`scripts/fetch_jwks.py`)
- Document hostnames/audiences for each client; ensure MFA flags/claims included in tokens. ✅ (see README clients/audiences; MFA claims to be extended with policies later)

## Tests / Validation
- On `docker compose up`, realm imports successfully (clients/roles visible).
- Fetch JWKS via script; validate a sample token using python-keycloak.
- Generate test users/roles; confirm token contains expected roles/claims. 

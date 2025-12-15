# Production Security & Hardening Plan

Actionable items to move from dev-friendly defaults to production-grade posture. Each item assumes `DJANGO_SETTINGS_MODULE=config.settings.production`.

## Transport & Identity
- Cerbos client: set `tls_verify=True` (default in prod settings) and provide CA bundle or mTLS. Fail fast if disabled.
- Keycloak token validation: enforce strict issuers and per-surface audiences (`api`, `global-admin`, `org-admin`); reject tokens without matching `aud/azp`.
- Local JWTs: require configured signing/verification keys, enforce audience, and disable auto-generated dev keys.
- Admin hostname: set `ADMIN_HOSTNAME` and route `/admin` only via that host. Consider separate host/path for platform admin APIs.

## Authorization Scope
- Principal building: limit membership/role attrs to the org/team in the request or token; do not merge cross-tenant memberships. Add tests to prevent bleed.
- Cerbos cache: isolate to its own cache alias/prefix and add targeted invalidation.

## Access Keys (AKSK)
- Strengthen signature to include host, canonical path+query, and body hash; add a nonce/idempotency key and shorten the timestamp window. Reject clock-skewed or replayed requests.
- Store/display secrets once; ensure encryption keys are set.

## Impersonation
- Require MFA claims on the admin token. Read roles from `realm_access`/`resource_access`.
- Disallow creating users during impersonation; target user must already exist and belong to the appropriate org.
- Keep audit logging mandatory for impersonation start/end/actions.

## Throttling & Abuse
- Resolve `org_id` after authentication (claims/membership) and reject caller-supplied org_ids that differ. Maintain per-org throttling with tier/feature-flag overrides.
- Keep anon/user throttles enabled; tighten defaults as needed.

## Tokens & Sessions
- Refresh tokens: implement rotation + reuse detection; bind to device metadata; revoke family on reuse.
- Email verification/password reset tokens: store hashed (constant-time compare) with expiries; purge after use.
- Enforce MFA where required (`MFA_REQUIRED_FOR_ADMIN=true`), and propagate MFA level to Cerbos principal attrs.

## Settings & Secrets
- SECRET_KEY must be set (production settings already fail if default). DEBUG must be false.
- CSP: remove `'unsafe-inline'`; set explicit `CSP_*` for your frontend. CORS: explicit allowed origins only.
- Configure `FIELD_ENCRYPTION_KEYS`, `AUDIT_SIGNING_KEY`, Stripe keys, and other secrets via a secret manager; no defaults.
- Disable local auth if not needed (`LOCAL_AUTH_ENABLED=false`) or lock it down (strong password policy, email verification required).

## Data Protection
- Ensure S3/MinIO creds and buckets are configured if using object storage; enforce TLS to storage.
- Encrypt sensitive fields via configured keys; consider hashing for lookup fields where needed.

## Observability & Compliance
- Enable Sentry with PII scrubbing; ship structured logs to SIEM. Keep audit chain verification on.
- Monitor rate-limit hits, Cerbos decision latency, Keycloak/JWT failures, Celery DLQ, and DB/Redis health.
- Generate and retain SBOM (CI already generates `sbom.json`); add image signing and vulnerability gating as policy requires.

## Deployment & Network
- Force HTTPS (settings.production already set) with HSTS; ensure proxy headers configured.
- Segment admin and API surfaces; restrict admin ingress/IPs if possible. Consider WAF/rate limits at edge.
- Rotate keys regularly (JWT, Cerbos, AKSK, FIELD_ENCRYPTION_KEYS); maintain runbooks and automate where possible.

## Frontend (React Admin)
- Transport: ensure `VITE_API_URL` and `VITE_KEYCLOAK_URL` point to HTTPS origins; disable OIDC silent renew over HTTP; align client IDs/audiences with backend enforcement.
- Token handling: OIDC/local tokens currently live in `sessionStorage`; for prod prefer OIDC-only with PKCE and (if feasible) httpOnly/secure cookies for session. If tokens stay in JS, enforce strict CSP (no inline scripts), lint for XSS, and avoid rendering untrusted HTML.
- RBAC gating: add route guards that check parsed roles/tenant (`frontend/src/lib/auth/parse-user.ts`) to mirror backend authz; don’t rely solely on 403s.
- WebSockets: `ws-client` appends tokens in query params; move to `wss://` with header/subprotocol or short-lived signed token, set server-side max TTL/idle, and reject query-token auth.
- Logout/reuse: frontend only clears storage; rely on backend refresh rotation/reuse detection and consider binding token family to device metadata server-side.
- Build hygiene: disable source maps in prod builds, ensure dev tools stay dev-only.

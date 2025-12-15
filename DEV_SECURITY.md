# Dev Environment Security & Ops Notes

Practical guardrails for local/dev. Assumes convenience > hard guarantees; document gaps so prod plan can lock down.

## AuthN/AuthZ
- Cerbos client: allow `tls_verify=False` locally (self-signed/HTTP). Keep flagged in settings.local and log a warning.
- Token audience: lenient is acceptable for quick local runs; keep clear that prod enforces per-audience.
- Impersonation: only enable when explicitly toggled (`IMPERSONATION_ENABLED=true`). Allow current get-or-create behavior for demos, but avoid using real data.
- Access keys: current signature (timestamp+method+path, 5m window) is ok for local; educate that it’s replayable.
- Org throttling: query-param org selection is acceptable for smoke tests; expect bypassability.

## Data Handling
- Email verification/password reset tokens are stored in plaintext; acceptable for local databases. Never reuse local DB in higher environments.
- Encryption keys (`FIELD_ENCRYPTION_KEYS`) can be blank; features depending on them may no-op. Use a throwaway key if exercising encrypted fields.

## Settings
- DEBUG may be true; SECRET_KEY may be default. Use `.env` with non-sensitive values; never promote to prod.
- CSP is relaxed (`'unsafe-inline'`), CORS wide; fine for local.
- Admin hostname guard optional; Django admin can live on same host.

## Tokens & Sessions
- Refresh tokens are non-rotating; reuse not detected. Acceptable locally.
- MFA optional; local auth enabled by default.

## Networking/Transport
- HTTP between services is fine (Keycloak/Cerbos/Postgres/Redis/RabbitMQ).
- Sentry/metrics optional; stubs are fine.

## Observability & Logs
- Logs may include PII (structlog redactor still runs). Keep data non-sensitive.
- Rate limiting defaults: anon/user/org throttles present but org throttle can be bypassed via `org_id` param.

## CI/Test Considerations
- CI uses Postgres/Redis and Cerbos container; ensure `.env.test` mirrors lenient settings (no TLS).
- If adding tests for hardened behaviors, gate them with env flags so dev defaults stay passing.

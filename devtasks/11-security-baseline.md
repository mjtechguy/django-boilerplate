# Plan 11: Security Hardening Baseline

## Tasks
- Enforce HTTPS settings (SECURE_*), HSTS (env-gated), secure cookies.
- Configure django-axes for local auth endpoints; rate limiting with Redis keys per tenant/user.
- Apply CORS allowlist (env-driven) and CSP baseline (django-csp).
- Secrets: load from env; `.env.example` only; document dev vs prod secret handling (secret manager later).
- Admin surfaces on separate hostnames; ensure no mixed routing with end-user APIs.
- Optional WAF/API gateway notes for prod.

## Tests / Validation
- Unit: middleware/settings presence.
- Integration: CORS rejects disallowed origins; HSTS present in prod mode; admin endpoints not reachable from end-user audience.
- Security scan: basic lint/check for missing SECURE_* in prod settings. 

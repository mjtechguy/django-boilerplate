# MVP Task Plan (Implementation Order)

## 0. Repo + Tooling Baseline
- Initialize repo structure; add `.gitignore`, `.env.example` (no secrets), pre-commit with ruff/pytest hooks.
- Add `uv` (preferred) or pip lockfile; pin dependencies per PRD (Django, DRF, psycopg, python-keycloak, cerbos, django-redis, redis, celery, rabbitmq client defaults, django-axes, django-cors-headers, django-csp, sentry-sdk, structlog, ruff, pytest, coverage, django-storages, boto3).
- Add basic CI: ruff, pytest (placeholder), pip-audit/safety, container scan placeholder.

## 1. Core Services & Containers
- Author Dockerfiles (slim base) for Django app (web/worker/beat entrypoints).
- Docker Compose for dev: web, postgres, redis, rabbitmq, keycloak, cerbos, celery, celery-beat, optional stripe-mock, optional s3/minio (for storage), healthchecks.
- Ensure env wiring for secrets/config; mount volumes for Keycloak realm import and Cerbos policy bundle.

## 2. Django/DRF Project Setup
- Create Django project/app; configure Postgres via psycopg pool; set timezone, language, static/media configs; add S3/minio storage optional backend via django-storages/boto3.
- Add DRF setup (default auth classes placeholder, pagination, versioned API prefix `/api/v1`).
- Add structlog JSON logging, request IDs/trace IDs middleware, Sentry init (env-gated).
- Add CORS (django-cors-headers) and CSP (django-csp) baseline.

## 3. Keycloak Integration
- Import seed realm/clients via Keycloak container entrypoint/realm JSON: distinct clients for global admin, org admin, end-user.
- Document hostnames/audiences for each; ensure MFA flags/claims in tokens where applicable.
- Add python-keycloak utilities for JWKS fetch/cache and admin ops (to be used in management scripts).

## 4. Auth Pipeline (DRF)
- Implement DRF authentication class (or thin wrapper if using drf-keycloak) to validate JWTs (issuer/audience/exp/sig), extract realm + client roles, tenant/org claims, MFA flags.
- Map to lightweight shadow User model (Keycloak sub as PK), with org linkage placeholder.
- Enforce versioned routes; add idempotency key middleware for mutating endpoints (store in Redis).

## 5. Data Model (AuthZ-Relevant)
- Migrate initial models: User (shadow), Org, Team, Membership (org_roles, team_roles), Settings (scoped key/value for org/global), Resource base tagging org_id/team_id.
- Include fields for license_tier, feature_flags in Org/Settings.
- Add sensitivity/pii flags to relevant resource placeholders.

## 6. Cerbos Integration
- Add Cerbos client (gRPC) config; load host/port from env; establish healthcheck.
- Implement permission helper to build principal/resource payloads (realm/client roles, org_id, team_ids, license_tier, mfa_level, risk flags).
- Add a sample Cerbos policy bundle (patient_record/project/doc) checked into repo; wire mount into Cerbos container.
- Add decision caching (short TTL) with Redis; cache key strategy and invalidation hooks.

## 7. Licensing/Stripe (Optional but Wired)
- Add settings table accessors to read/write license_tier and feature_flags (env defaults → DB overrides).
- Add API endpoints (role-gated) to read/update org license/flags; audit changes; trigger cache/Cerbos invalidation.
- Stub Stripe integration (webhook endpoint, secret config) to map product/price → tier/flags; store last sync status.

## 8. Admin vs Org Admin vs End-User Separation
- Set up routing/namespaces for global admin API vs org admin API vs end-user API; distinct auth audiences enforced.
- Add sample endpoints for org admin (manage org, teams, memberships) and global admin (support-readonly, policy/version info).
- Ensure Cerbos policies align with these boundaries; deny cross-tenant by default.

## 9. Async + Broker
- Configure Celery with RabbitMQ broker, Redis backend/locks; set task_acks_late, retries/backoff, dedup keys, DLQ routing.
- Add healthchecks/metrics for Celery and RabbitMQ.
- Add a sample idempotent task (e.g., audit log fan-out) with retry/metrics.

## 10. Security Hardening Baseline
- Enforce HTTPS settings (SECURE_*), HSTS (env-gated), secure cookies.
- Add django-axes for any local auth endpoints (admin); rate limits via Redis keys per tenant/user.
- Add CSP baseline; tighten CORS allowlist via env.
- Secrets from env; `.env.example` only; document secret management (dev vs prod).

## 11. Observability
- Metrics endpoints (Prometheus format if possible) covering Django, Celery, Cerbos client latency, RabbitMQ queue/DLQ depth (via exporter), Redis stats.
- Logging fields: request_id/trace_id, actor, org_id, route, decision_id, policy_version, outcome.
- Sentry configured for web + Celery; env toggles for dev/stage/prod.

## 12. Testing & CI
- Add pytest skeletons for auth class, settings precedence, Cerbos permission helper, idempotency middleware.
- Add contract tests for Cerbos policies (using sample bundle).
- CI: ruff, pytest, dependency scan, container build + scan.

## 13. Documentation
- Update README/PRD summary for local dev flow (uv/pip install, compose up, migrate, seed Keycloak/Cerbos, sample calls).
- Docs for admin vs org admin API audiences, env vars, and how to switch storage to S3/MinIO.

## 14. Stretch (Post-MVP readiness)
- Backup/PITR setup for Postgres (doc placeholder).
- SBOM/image signing pipeline placeholder.
- Optional mTLS/internal TLS and WAF notes for prod.

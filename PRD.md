# PRD: High-Scale AuthZ/API Platform (Django + DRF + Keycloak + Cerbos)

## 1) Goal and Success Criteria
- Deliver a multi-tenant, high-scale API platform with granular RBAC + ABAC across platform, org, team, and user levels.
- AuthN via Keycloak; AuthZ via Cerbos; Django/DRF for APIs; Postgres as the primary store.
- Development runs on Docker with separate containers: Django web, Postgres, Keycloak, Cerbos, Redis, Celery worker/beat; optional Stripe mock/connector.
- P99 end-to-end request (including authz) < 300ms at target load; Cerbos gRPC check < 20ms P99 at 2k RPS per node.
- Clean separation of IdP (Keycloak) and PDP (Cerbos); auditable policy changes; zero-downtime deploys for policies and app.

## 2) Scope and Non-Goals
- In scope: AuthN, AuthZ, multi-tenancy isolation, policy-driven RBAC/ABAC, auditability, observability, rate limiting, configuration via env + DB overrides, licensing/tier gating with optional Stripe integration, Dockerized dev environment.
- Out of scope: Frontend implementation, detailed UI/UX for portals, data science/analytics pipelines, billing UI.

## 3) Core Stack (versions pinned)
- Django==6.0 (or Django 5.2 LTS fallback if risk-averse).
- djangorestframework==3.16.1.
- Postgres via psycopg[binary,pool]==3.3.2.
- Keycloak (IdP) with python-keycloak==5.8.1 for admin/token ops.
- Cerbos==0.7.0 Python SDK (gRPC client preferred).
- Security: django-axes==8.0.0, django-cors-headers==4.9.0, django-csp==4.0.
- Caching/async: django-redis==6.0.0, redis==7.0.1, celery==5.6.0 (RabbitMQ broker recommended; Redis kept for cache/rate limits/locks).
- Observability: sentry-sdk==2.47.0.
- Dev tooling: ruff (lint/format), structlog (structured JSON logs), pytest, coverage, pre-commit hooks.

### Example requirements.txt (baseline)
```
# Core framework + API
Django==6.0
djangorestframework==3.16.1

# Database / Postgres
psycopg[binary,pool]==3.3.2

# Keycloak integration (IdP / OIDC / JWT)
python-keycloak==5.8.1
# optional DRF helper:
# drf-keycloak==<latest>

# Cerbos authorization client (RBAC + ABAC at scale)
cerbos==0.7.0

# Security / hardening
django-axes==8.0.0
django-cors-headers==4.9.0
django-csp==4.0

# Caching / async tasks
django-redis==6.0.0
redis==7.0.1
celery==5.6.0

# Observability
sentry-sdk==2.47.0

# Dev tooling (pin in dev extras)
ruff
structlog
pytest
coverage

# Optional storage
django-storages
boto3
```

## 3b) Developer Tooling & Local DX
- Package/install: prefer `uv` for fast, reproducible envs; fall back to `pip` if required. Keep lockfile/checksums in repo.
- Code quality: ruff for lint/format; pre-commit to enforce; mypy optional if/when type coverage grows.
- Logging: structlog for structured logs; align fields with authz/audit requirements.
- Testing: pytest + coverage; add Cerbos policy contract tests in CI.
- Git hooks/CI: run ruff, tests, and policy checks in CI; block merges on failures.

## 4) Role Model (Realm vs Client Roles)
- Split: platform/global roles → Keycloak realm roles; per-application/tenant roles → client roles on the API client. Keep mapping simple and project into Cerbos principal attrs.
- Examples:
  - Realm roles (global): platform_admin, support_readonly.
  - Client roles (API client): org_admin, org_member, team_admin, team_member, billing_admin.
- Token handling: DRF auth class validates audience and extracts both realm and client roles; maps to principal roles and attrs for Cerbos.

## 5) AuthN + AuthZ Flows
1. Frontend authenticates via Keycloak (OIDC), receives JWT access token.
2. Frontend calls Django API with `Authorization: Bearer <token>`.
3. DRF auth class (custom or drf-keycloak) validates signature, issuer, audience, expiry; pulls realm/client roles and tenant claims; syncs lightweight Django `User` shadow (keyed by `sub`).
4. Permission layer builds Cerbos principal/resource:
   - Principal: id, roles (realm + client), attrs {platform_role, org_id, team_ids, license_tier, risk_flags, feature_flags, device_risk, mfa_level}.
   - Resource: kind, id, attrs {org_id, team_id, owner_id, status, sensitivity, pii_flags}.
5. Django (PEP) calls Cerbos (PDP) via gRPC; Cerbos returns allow/deny per action; Django enforces 403 on deny.
6. Defaults: deny by default; cross-tenant access denied unless platform role allows with guardrails.

## 6) Policy Design (RBAC + ABAC)
- Resource kinds: patient_record, project, document, billing_account, audit_log, feature_flag.
- Actions: read, create, update, delete, admin, export, invite.
- Attributes:
  - Principal: platform_role, org_id, org_roles, team_ids, team_roles, license_tier, risk_flags, mfa_level.
  - Resource: org_id, team_id, owner_id, status, sensitivity, pii_flags, billing_status.
- Patterns:
  - Platform realm roles permit cross-tenant actions only where explicitly allowed (support_readonly with scoped mask).
  - Org isolation: principal.org_id must match resource.org_id unless platform override.
  - Team scoping: team_roles + team_id required for team-owned resources.
  - Ownership: owners can read/update unless sensitivity/policy blocks.
  - ABAC: sensitivity + pii_flags can require higher mfa_level or platform role; billing_status/ license_tier gates create/export actions.

## 7) Licensing and Feature Gating (with optional Stripe)
- Data sources:
  - Env defaults: `LICENSE_TIER_DEFAULT`, `LICENSE_FEATURE_FLAGS_DEFAULT`.
  - DB-configurable per tenant: `license_tier`, `feature_flags` stored in a settings table (tenant-aware).
  - Stripe (optional): subscription status and product/price map to `license_tier` + feature flags; sync via webhook/cron into DB settings.
- API exposure: all licensing state (tier, feature flags, Stripe status, last-sync) exposed via authenticated admin/org APIs for the future frontend to manage and monitor. Mutations go through audited endpoints that update DB settings and trigger Cerbos cache invalidation.
- Enforcement split:
  - App-side: UI/route gating and fast checks before expensive work (e.g., hide features, skip job enqueue if disabled).
  - Cerbos-side: protected actions (e.g., `create_project`, `export_data`) include `license_tier` and `feature_flags` in principal attrs so policies enforce tier rules consistently across services.
- Fail-safe: if Stripe unreachable, fall back to last known tier/flags; log and alert.

## 8) Configurability (Env + DB Overrides)
- Environment variables (examples):
  - AUTHZ_FAIL_MODE: `fail_closed` | `fail_open_low_risk` (default: fail_closed).
  - AUDIT_RETENTION_DAYS (default: 90).
  - AUDIT_PII_POLICY: `mask` | `hash` | `drop` (default: mask).
  - LICENSE_TIER_DEFAULT (default: free).
  - LICENSE_FEATURE_FLAGS_DEFAULT (default: none/CSV).
  - STRIPE_ENABLED: `true|false`; STRIPE_API_KEY; STRIPE_WEBHOOK_SECRET.
- Database settings table (tenant-aware when multi-tenant) to override env defaults:
  - audit_retention_days, audit_pii_policy, audit_export_destination.
  - authz_fail_mode (per tenant optional).
  - license_tier, feature_flags.
- Precedence: DB per-tenant override → DB global override → env default.
- Celery tasks enforce retention and PII handling according to these settings.
- API exposure: provide authenticated, role-gated admin/org endpoints to read/update these settings (fail mode, audit retention/PII policy, license tier/flags). All changes are audited and propagate invalidation to caches/Cerbos decision cache.

## 8b) API-First Control Plane and Portal Separation
- API-first: every configurable option (licensing, feature flags, fail modes, audit retention/PII policy, role assignments, team/org management, policy publish/version info, Stripe sync status) is exposed via authenticated APIs so the future frontend can fully manage the system.
- Portal separation for safety:
  - Global admin portal (and API audience) for platform-level controls: realms/clients bootstrap, global settings, policy versioning, cross-tenant support views, fail-mode toggles, Stripe/global billing config. Backed by a distinct Keycloak client/audience and DRF auth class to ensure strict separation.
  - Org admin portal (and API audience) for per-tenant controls: org settings, teams, users, memberships, org-scoped settings (license tier/flags, audit retention/PII policy, fail mode if allowed), billing status for that org. Uses org-scoped client roles and Cerbos enforcement to prevent cross-tenant access.
  - End-user portal/API audience for product use; no access to admin endpoints.
- Duplicate endpoints where needed (global vs org admin variants) to keep boundaries hard and avoid accidental elevation. Each surface has separate authz checks and routing; never co-mingle global admin routes with end-user routes.

## 9) Failure Modes (Fail-Closed vs Selective Fail-Open)
- Default: fail-closed (deny if Cerbos/Keycloak unavailable).
- Optional selective fail-open: small, explicit allowlist of low-risk read-only endpoints. Must be configured (env/DB), logged, and monitored. Never for PII/sensitive resources.
- Circuit breaker and backoff for Cerbos calls; health endpoints for readiness/liveness.

## 10) Data Model (AuthZ-relevant)
- User (shadow): id (Keycloak sub), email, status, last_login, mfa_level.
- Tenant/Org: id, name, status, license_tier, feature_flags (from settings).
- Team: id, org_id, name.
- Membership: user_id, org_id, team_id nullable, roles (org_roles, team_roles).
- Settings table: key/value with scope (global/org) for audit/licensing/fail-mode configs.
- Resource tables tagged with org_id (+ team_id where relevant); include sensitivity/pii flags where needed.

## 11) Auditability and PII Handling
- Log each authorization decision: actor, resource kind/id, action, result, policy version, decision_time_ms; strip or hash PII per policy.
- Keycloak admin actions (role grants, realm changes) logged.
- Retention enforced by Celery job honoring `audit_retention_days`; PII handling guided by `audit_pii_policy`.
- Decision logs may be forwarded to SIEM; redact fields before export if policy requires.

## 12) Observability and Operations
- Sentry for exceptions/perf traces (web + Celery).
- Structured JSON logs; trace IDs propagated to Cerbos calls.
- Metrics: Cerbos latency/allow-rate, cache hit rate, Keycloak token validation failures, rate limit triggers.
- Queues: RabbitMQ metrics (queue depth, DLQ depth, consumer lag), Celery task success/failure/retry counts.
- Health checks: web, Celery, Redis, Postgres, Keycloak, Cerbos; readiness gates traffic.

## 13) Caching, Rate Limiting, Security
- Decision caching: short TTL cache keyed by (principal hash, resource hash, action); invalidate on policy version change or role change when signaled.
- Redis-backed rate limits per tenant/user; django-axes for brute-force defense on local auth endpoints/admin.
- CORS via django-cors-headers; CSP via django-csp; HTTPS/TLS in prod; secrets via env/secret manager.
- Queuing: Celery with RabbitMQ broker for durable queues, DLQs/TTL, and routing; Redis reserved for cache/rate limits/locks.

## 13b) Enterprise-Grade Hardening & Operations
- Secrets/keys: external secret manager (Vault/SSM/Secrets Manager); no secrets in images; short-lived DB creds; rotate Keycloak/Cerbos keys; TLS everywhere; mTLS for service-to-service (mesh if available).
- Supply chain: minimal base images (distroless/ubi); SBOM generation; image signing (cosign); dependency scanning (pip-audit/safety) and container scanning in CI; pin/lock dependencies.
- Data protection: Postgres encryption at rest (disk/KMS); field-level encryption for sensitive columns where required; PITR backups (WAL archiving) + tested restores; multi-AZ DB; DR plan/runbook.
- Networking/AppSec: WAF/API gateway with rate limiting and IP allow/deny lists where needed; DDoS protections at edge; strict CORS; CSP/SEC headers; admin portals on separate hostnames and clients.
- Identity boundaries: distinct Keycloak clients/audiences for global admin vs org admin vs end-user; conditional MFA for sensitive actions; device/IP risk attributes plumbed to Cerbos where applicable.
- API design: versioned APIs; idempotency keys for mutating endpoints; pagination; 429 and retry semantics defined.
- Jobs robustness: idempotent Celery tasks; dedup keys; retries with backoff; DLQ monitoring; tasks avoid side effects before ack.
- Observability/SLOs: SLOs for authz latency, API latency, task success; alerts on Cerbos/Keycloak health, RabbitMQ depth/DLQ, DB replication lag, Redis evictions; structured logs with PII redaction.
- Change management: policy repo with CI tests; infrastructure as code; staged rollouts/blue-green; feature flags for risky changes; runbooks for outages and failover.

## 13c) Day-One Must-Haves (to build in from the start)
- Identity boundaries: separate Keycloak clients/audiences for global admin vs org admin vs end-user; distinct hostnames for admin vs user APIs; enforce MFA flags/claims in tokens and pass to Cerbos.
- API versioning/idempotency: versioned routes (e.g., /api/v1); idempotency keys on mutating endpoints; pagination; 429/retry semantics defined.
- Job robustness: idempotent Celery tasks; retries with exponential backoff; task_acks_late; dedup keys; DLQ wiring in RabbitMQ.
- Observability basics: structured JSON logs (structlog), trace IDs, Sentry, metrics for Cerbos/Keycloak/RabbitMQ/DB/Redis, health/readiness probes.
- Secrets: never bake secrets into images; use env/secret manager plumbing even in dev/stage; configs for Keycloak/Cerbos/DB keys are rotateable.
- Supply chain hygiene: pinned deps + lockfile; ruff/pytest in CI; dependency scan (pip-audit/safety) and container scan; slim base images.

## 13d) High-Assurance / Regulated (HIPAA, HITRUST, FedRAMP/Defense)
- Crypto: FIPS 140-2 validated TLS/crypto where required; TLS 1.2+/1.3; mTLS for internal calls; manage signing keys (Keycloak/Cerbos JWT) in KMS/HSM; certificate rotation and pinning policies.
- Audit/forensics: tamper-evident audit logs (hash/WORM storage), NTP-synchronized clocks, log signing; capture admin actions, policy changes, role grants, authz decisions; ship to SIEM with retention controls.
- Data handling: PHI/PII classification and minimization; row-level and field-level protections (RLS plus field encryption for sensitive columns); data residency awareness; backups encrypted at rest/in transit.
- Access control: least-privileged IAM for infra; JIT/break-glass with recording; strong MFA everywhere; device posture signals fed into Cerbos when available.
- Network/segmentation: private networking, egress controls, no public DB; WAF/API gateway with IP allow/deny; admin surfaces on separate hostnames and client audiences.
- DR/BCP: defined RPO/RTO per service; tested restores and DR drills; multi-AZ DB; documented failover runbooks.
- Compliance operations: SBOM + image signing; container and dependency scanning; evidence collection for SOC 2/ISO 27001/HIPAA; FedRAMP/IL4+/STIG hardening where applicable; change control with approvals and trails.
- Monitoring/detection: SIEM ingestion, UEBA/anomaly detection on auth patterns; alerting on policy tampering, key rotation failures, DLQ growth, DB replication lag.

## 14) Deployment and Dev Environment
- Docker Compose services: web (Django), db (Postgres), keycloak, cerbos, redis, rabbitmq (Celery broker), celery, celery-beat, optional stripe-mock; each with healthchecks.
- Process-per-concern containers (same code image for app/worker/beat):
  - web: Django API, stateless, horizontal scale.
  - celery: background workers, horizontal scale independent of web.
  - celery-beat: scheduler.
  - cerbos: separate PDP service; horizontal scale; expose gRPC internally.
  - keycloak: separate IdP; backed by Postgres (or dedicated schema).
  - postgres: stateful DB.
  - redis: cache/rate limit/locks.
  - rabbitmq: durable message broker with DLQs/TTL for Celery.
- Migrations via Django; policy bundle mounted or pulled into Cerbos container; Keycloak realm import for seed roles/clients.
- Horizontal scalability: stateless web/Celery; Cerbos replicated with gRPC; Postgres with connection pooling.
- Future production: Kubernetes for service orchestration (app, Celery, Cerbos, Keycloak, Redis); use gRPC service for Cerbos behind an internal LB; leverage K8s secrets and HPAs; keep Docker images consistent across dev/prod.

## 15) Testing Strategy
- Unit: permission classes, token verifier, settings precedence logic.
- Integration: DRF + Keycloak JWT validation; Cerbos policy checks against fixtures; licensing gates with and without Stripe.
- Contract: Cerbos policy tests in CI; policy linting; sample decisions.
- Load: authz path at target RPS; cache effectiveness.

## 16) Open/Confirm Decisions
- Default realm/client role names and claim shapes (needs agreement).
- Stripe product → tier/feature map (SKUs and flags).
- Exact allowlist (if any) for selective fail-open.
- PII fields list for masking/hashing.

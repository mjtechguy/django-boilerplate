# Django + DRF + Keycloak + Cerbos Boilerplate (High-Scale RBAC/ABAC)

Production-ready, multi-tenant SaaS boilerplate with enterprise security features. Includes RBAC/ABAC authorization (Cerbos), hybrid authentication (Keycloak + Local), Stripe billing (B2B & B2C), React admin console, and comprehensive audit logging.

## Table of Contents

- [Features](#features)
- [Service Topology](#service-topology)
- [Quickstart](#quickstart)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Stripe Billing](#stripe-billing)
- [Frontend Admin Console](#frontend-admin-console)
- [Audit Trail](#audit-trail)
- [Custom Webhooks](#custom-webhooks)
- [Storage Configuration](#storage-configuration)
- [Runbooks](#runbooks)
- [Architecture Overview](#architecture-overview)
- [Testing](#testing)

## Features

### Security & Authentication
- **Hybrid Auth**: Keycloak OIDC + Local JWT (RS256) authentication
- **RBAC/ABAC**: Cerbos policy decision point with Redis-cached decisions
- **Argon2 Passwords**: Industry-standard password hashing
- **MFA Support**: Multi-factor authentication via Keycloak
- **Account Lockout**: Brute-force protection with django-axes
- **Rate Limiting**: Global and per-tenant throttling

### Multi-Tenancy
- **Organizations**: Multi-org data isolation
- **Teams**: Org-scoped team management
- **Memberships**: Flexible role assignments (org_roles, team_roles)
- **License Tiers**: Per-org feature gating (free, starter, pro, enterprise)

### Billing (Stripe)
- **B2B Org Billing**: Organization-level subscriptions
- **B2C User Billing**: Individual user subscriptions
- **Webhook Handling**: Automatic tier updates on subscription events
- **Billing Portal**: Self-service subscription management

### Admin Console (React)
- **Organizations Management**: CRUD with license management
- **Teams Management**: Create/edit teams with member management
- **Users Management**: Invite, create, deactivate users
- **Audit Log Viewer**: Search, filter, export audit logs
- **System Monitoring**: Celery health, queue stats, metrics

### Observability
- **Structured Logging**: JSON logs with structlog
- **Audit Trail**: Tamper-evident logs with hash chain verification
- **Prometheus Metrics**: `/api/v1/monitoring/metrics`
- **Sentry Integration**: Error tracking and tracing
- **Health Probes**: Kubernetes-ready liveness/readiness

## Service Topology

Development stack via Docker Compose:

| Service | Description | Port |
|---------|-------------|------|
| web | Django/DRF API (stateless) | 8000 |
| frontend | React Admin Console (Vite) | 5173 |
| celery | Celery workers (async tasks) | - |
| celery-beat | Celery scheduler | - |
| cerbos | Policy Decision Point (RBAC/ABAC) | 3592, 3593 |
| keycloak | Identity Provider (OIDC) | 8080 |
| postgres | Primary database | 5432 |
| rabbitmq | Celery broker (durable queues + DLQ) | 5672, 15672 |
| redis | Cache, rate limits, locks | 6379 |
| mailpit | Email testing (dev only) | 8025, 1025 |
| stripe-mock | Stripe API mock (dev only) | 12111 |

```mermaid
flowchart LR
  FE[React Admin] -->|OIDC/Local| KC[Keycloak]
  FE -->|Bearer JWT| WEB[Django API]
  WEB -->|gRPC allow/deny| CER[Cerbos]
  WEB -->|SQL| PG[(Postgres)]
  WEB -->|cache/rate| RDS[(Redis)]
  WEB -->|Stripe API| STRIPE[Stripe]
  CEL[Celery Worker] -->|tasks| RMQ[(RabbitMQ)]
  BEAT[Celery Beat] --> RMQ
```

## Quickstart

### Prerequisites

- Python 3.13+
- Node.js 20+ (for frontend)
- Docker and Docker Compose
- `uv` (recommended) or `pip`

### 1. Clone and Setup

```bash
git clone <repo-url>
cd django-boilerplate

# Backend: Create virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Frontend: Install dependencies
cd frontend && pnpm install && cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values (defaults work for local dev)
```

### 3. Start Services

```bash
# Start all services
docker compose -f compose/docker-compose.yml up -d

# Wait for services to be healthy (~30s for Keycloak)
docker compose -f compose/docker-compose.yml ps

# Run database migrations
docker compose -f compose/docker-compose.yml exec -w /app/backend web python manage.py migrate
```

### 4. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| Admin Console | http://localhost:5173 | See below |
| Keycloak Admin | http://localhost:8080 | admin / admin |
| RabbitMQ | http://localhost:15672 | guest / guest |
| Mailpit | http://localhost:8025 | - |

### 5. Create Admin User (Local Auth)

```bash
# Register via API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "SecurePass123!", "first_name": "Admin", "last_name": "User"}'

# Or use Django management command
docker compose -f compose/docker-compose.yml exec -w /app/backend web \
  python manage.py createsuperuser
```

## Environment Variables

### Core Django

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Secret key (change in production!) | `changeme` |
| `DJANGO_DEBUG` | Enable debug mode | `true` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `config.settings.local` |
| `FRONTEND_URL` | Frontend URL for redirects | `http://localhost:5173` |

### Database (PostgreSQL)

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `app` |
| `POSTGRES_USER` | Database user | `app` |
| `POSTGRES_PASSWORD` | Database password | `changeme` |
| `POSTGRES_HOST` | Database host | `postgres` |
| `POSTGRES_PORT` | Database port | `5432` |

### Redis & RabbitMQ

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `RABBITMQ_HOST` | RabbitMQ host | `rabbitmq` |
| `RABBITMQ_USER` | RabbitMQ user | `guest` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `guest` |

### Authentication (Keycloak)

| Variable | Description | Default |
|----------|-------------|---------|
| `KEYCLOAK_SERVER_URL` | Keycloak server URL | `http://keycloak:8080` |
| `KEYCLOAK_REALM` | Keycloak realm | `app` |
| `KEYCLOAK_CLIENT_ID` | Keycloak client ID | `api` |
| `KEYCLOAK_AUDIENCE` | Expected JWT audience | `api` |

### Local Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCAL_AUTH_ENABLED` | Enable local auth | `true` |
| `LOCAL_AUTH_ACCESS_TOKEN_TTL` | Access token TTL (seconds) | `900` |
| `LOCAL_AUTH_REFRESH_TOKEN_TTL` | Refresh token TTL (seconds) | `604800` |
| `LOCAL_AUTH_MAX_FAILED_ATTEMPTS` | Max failed logins before lockout | `5` |
| `LOCAL_AUTH_LOCKOUT_DURATION` | Lockout duration (seconds) | `1800` |
| `EMAIL_VERIFICATION_REQUIRED` | Require email verification | `true` |

### Authorization (Cerbos)

| Variable | Description | Default |
|----------|-------------|---------|
| `CERBOS_URL` | Cerbos server URL | `http://cerbos:3592` |
| `CERBOS_DECISION_CACHE_TTL` | Decision cache TTL (seconds) | `30` |

### Stripe Billing

| Variable | Description | Default |
|----------|-------------|---------|
| `STRIPE_ENABLED` | Enable Stripe integration | `false` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | `` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `` |
| `STRIPE_PRICE_STARTER` | Price ID for starter tier | `price_starter` |
| `STRIPE_PRICE_PRO` | Price ID for pro tier | `price_pro` |
| `STRIPE_PRICE_ENTERPRISE` | Price ID for enterprise tier | `price_enterprise` |

### Email

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_BACKEND` | Django email backend | `console` |
| `EMAIL_HOST` | SMTP host | `mailpit` |
| `EMAIL_PORT` | SMTP port | `1025` |
| `EMAIL_USE_TLS` | Use TLS | `false` |
| `DEFAULT_FROM_EMAIL` | Default sender email | `noreply@example.com` |

### Security

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_HOSTNAME` | Hostname for Django admin (production) | `` |
| `AXES_FAILURE_LIMIT` | Login failures before lockout | `5` |
| `AXES_COOLOFF_TIME` | Lockout duration (hours) | `1` |
| `THROTTLE_RATE_ANON` | Anonymous rate limit | `100/hour` |
| `THROTTLE_RATE_USER` | Authenticated rate limit | `1000/hour` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

### Observability

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Environment name | `development` |
| `AUDIT_PII_POLICY` | PII handling: mask, hash, drop | `mask` |
| `SENTRY_DSN` | Sentry DSN (empty to disable) | `` |

## API Reference

### Health & Monitoring

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/healthz` | GET | No | Basic health check |
| `/api/v1/health/live` | GET | No | Kubernetes liveness probe |
| `/api/v1/health/ready` | GET | No | Kubernetes readiness probe |
| `/api/v1/monitoring/overview` | GET | Admin | System overview |
| `/api/v1/monitoring/server` | GET | Admin | Server metrics |
| `/api/v1/monitoring/metrics` | GET | No | Prometheus metrics |
| `/api/v1/monitoring/metrics/json` | GET | No | JSON metrics |
| `/api/v1/monitoring/celery/health` | GET | No | Celery worker health |
| `/api/v1/monitoring/celery/stats` | GET | No | Celery statistics |
| `/api/v1/monitoring/queues` | GET | No | RabbitMQ queue stats |
| `/api/v1/monitoring/tasks` | GET | No | Registered Celery tasks |

### Local Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | No | Register new user |
| `/api/v1/auth/login` | POST | No | Login (returns JWT tokens) |
| `/api/v1/auth/logout` | POST | JWT | Logout (revoke refresh token) |
| `/api/v1/auth/refresh` | POST | No | Refresh access token |
| `/api/v1/auth/me` | GET | JWT | Get current user profile |
| `/api/v1/auth/verify-email` | POST | No | Verify email with token |
| `/api/v1/auth/resend-verification` | POST | No | Resend verification email |
| `/api/v1/auth/forgot-password` | POST | No | Request password reset |
| `/api/v1/auth/reset-password` | POST | No | Reset password with token |
| `/api/v1/auth/change-password` | POST | JWT | Change password (authenticated) |

### Keycloak Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/ping` | GET | JWT | Auth verification endpoint |
| `/api/v1/protected` | GET | JWT | Sample protected endpoint |

### B2B Organization Billing

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/orgs/{id}/billing` | GET | Org Admin | Get org billing status |
| `/api/v1/orgs/{id}/billing/checkout` | POST | Org Admin | Create Stripe checkout session |
| `/api/v1/orgs/{id}/billing/portal` | POST | Org Admin | Create billing portal session |
| `/api/v1/orgs/{id}/billing/customer` | POST | Org Admin | Create Stripe customer |
| `/api/v1/billing/plans` | GET | JWT | List available subscription plans |

### B2C User Billing

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/me/billing` | GET | JWT | Get user billing status |
| `/api/v1/me/billing/checkout` | POST | JWT | Create checkout session |
| `/api/v1/me/billing/portal` | POST | JWT | Create billing portal session |
| `/api/v1/me/billing/customer` | POST | JWT | Create Stripe customer |

### Organization Licensing

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/orgs/{id}/license` | GET | Org Admin | Get org license info |
| `/api/v1/orgs/{id}/license` | PUT | Org Admin | Update org license |
| `/api/v1/stripe/webhook` | POST | Stripe Sig | Stripe webhook handler |

### Platform Admin - Organizations

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/orgs` | GET | Platform Admin | List all organizations |
| `/api/v1/admin/orgs` | POST | Platform Admin | Create organization |
| `/api/v1/admin/orgs/{id}` | GET | Platform Admin | Get organization details |
| `/api/v1/admin/orgs/{id}` | PUT | Platform Admin | Update organization |
| `/api/v1/admin/orgs/{id}` | DELETE | Platform Admin | Soft-delete organization |

### Platform Admin - Teams

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/teams` | GET | Platform Admin | List all teams |
| `/api/v1/admin/teams` | POST | Platform Admin | Create team |
| `/api/v1/admin/teams/{id}` | GET | Platform Admin | Get team details |
| `/api/v1/admin/teams/{id}` | PUT | Platform Admin | Update team |
| `/api/v1/admin/teams/{id}` | DELETE | Platform Admin | Delete team |
| `/api/v1/admin/teams/{id}/members` | GET | Platform Admin | List team members |
| `/api/v1/admin/teams/{id}/members` | POST | Platform Admin | Add team member |

### Platform Admin - Users

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/users` | GET | Platform Admin | List all users |
| `/api/v1/admin/users` | POST | Platform Admin | Create user |
| `/api/v1/admin/users/invite` | POST | Platform Admin | Invite user via email |
| `/api/v1/admin/users/{id}` | GET | Platform Admin | Get user details |
| `/api/v1/admin/users/{id}` | PUT | Platform Admin | Update user |
| `/api/v1/admin/users/{id}` | DELETE | Platform Admin | Deactivate user |
| `/api/v1/admin/users/{id}/memberships` | GET | Platform Admin | List user memberships |
| `/api/v1/admin/users/{id}/memberships` | POST | Platform Admin | Add membership |
| `/api/v1/admin/users/{id}/resend-invite` | POST | Platform Admin | Resend invite email |

### Platform Admin - Memberships

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/memberships` | GET | Platform Admin | List all memberships |
| `/api/v1/admin/memberships` | POST | Platform Admin | Create membership |
| `/api/v1/admin/memberships/{id}` | GET | Platform Admin | Get membership details |
| `/api/v1/admin/memberships/{id}` | PUT | Platform Admin | Update membership roles |
| `/api/v1/admin/memberships/{id}` | DELETE | Platform Admin | Delete membership |

### Site Settings

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/settings/site` | GET | No | Get public site settings (branding) |
| `/api/v1/admin/settings/site` | GET | Platform Admin | Get admin site settings |
| `/api/v1/admin/settings/site` | PUT | Platform Admin | Update site settings |

### Audit Logs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/audit` | GET | JWT | List audit logs (filtered by access) |
| `/api/v1/audit/export` | GET | Platform Admin | Export audit logs (CSV/JSON) |
| `/api/v1/audit/verify` | POST | Platform Admin | Verify single audit entry |
| `/api/v1/audit/chain-verify` | POST | Platform Admin | Verify hash chain integrity |

### Custom Webhooks

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/webhooks` | GET | JWT | List webhook endpoints |
| `/api/v1/webhooks` | POST | JWT | Create webhook endpoint |
| `/api/v1/webhooks/{id}` | GET | JWT | Get webhook details |
| `/api/v1/webhooks/{id}` | PUT | JWT | Update webhook |
| `/api/v1/webhooks/{id}` | DELETE | JWT | Delete webhook |
| `/api/v1/webhooks/{id}/deliveries` | GET | JWT | List webhook deliveries |
| `/api/v1/webhooks/{id}/test` | POST | JWT | Send test webhook |

### Impersonation

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/impersonation/logs` | GET | Platform Admin | List impersonation logs |

### Alerts

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/alerts` | GET | Platform Admin | Get system alerts |

## Authentication

### Hybrid Authentication

The boilerplate supports two authentication methods that can work together:

1. **Keycloak OIDC**: Enterprise SSO with MFA support
2. **Local JWT**: Built-in username/password authentication

### Local Authentication Flow

```mermaid
sequenceDiagram
  participant U as User
  participant API as Django API
  participant DB as Database

  U->>API: POST /auth/register
  API->>DB: Create User + LocalUserProfile
  API->>U: Send verification email
  U->>API: POST /auth/verify-email
  API->>DB: Mark email verified
  U->>API: POST /auth/login
  API->>DB: Verify credentials
  API->>U: {access_token, refresh_token}
  U->>API: GET /api/... (Bearer token)
  API->>U: Response
```

### JWT Token Structure

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "name": "User Name",
  "realm_access": {
    "roles": ["user", "platform_admin"]
  },
  "org_id": "uuid",
  "team_ids": ["uuid1", "uuid2"],
  "iat": 1234567890,
  "exp": 1234568790
}
```

### Role Hierarchy

| Role | Scope | Permissions |
|------|-------|-------------|
| `platform_admin` | Global | Full system access |
| `org_admin` | Organization | Manage org teams/users |
| `team_admin` | Team | Manage team members |
| `user` | Self | Basic access |

## Stripe Billing

### B2B (Organization) Billing

Organization-level subscriptions for SaaS teams:

```bash
# Get billing status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/orgs/{org_id}/billing

# Create checkout session
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"price_id": "price_pro"}' \
  http://localhost:8000/api/v1/orgs/{org_id}/billing/checkout
```

### B2C (User) Billing

Individual user subscriptions:

```bash
# Get user billing status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/me/billing

# Create checkout session
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"price_id": "price_pro"}' \
  http://localhost:8000/api/v1/me/billing/checkout
```

### License Tiers & Features

| Tier | Default Features |
|------|------------------|
| `free` | 5 users, 1 team, 100 API req/hr |
| `starter` | 25 users, 5 teams, 1000 API req/hr |
| `pro` | 100 users, unlimited teams, 10000 API req/hr, webhooks |
| `enterprise` | Unlimited, custom features, audit export |

### Webhook Events Handled

- `checkout.session.completed` - Subscription activated
- `customer.subscription.created` - New subscription
- `customer.subscription.updated` - Plan changed
- `customer.subscription.deleted` - Subscription cancelled
- `invoice.payment_failed` - Payment failed

## Frontend Admin Console

### Overview

React-based admin console built with modern tooling:

- **React 18** with TypeScript
- **TanStack Router** - Type-safe routing
- **TanStack Query** - Server state management
- **TanStack Table** - Data tables with sorting/filtering
- **shadcn/ui** - Accessible UI components
- **Tailwind CSS** - Utility-first styling

### Pages

| Route | Description |
|-------|-------------|
| `/login` | Login page (local auth) |
| `/admin/organizations` | Manage organizations |
| `/admin/teams` | Manage teams |
| `/admin/users` | Manage users |
| `/admin/audit` | View audit logs |
| `/admin/monitoring` | System health dashboard |

### Running the Frontend

```bash
cd frontend
pnpm install
pnpm dev
# Open http://localhost:5173
```

### Building for Production

```bash
cd frontend
pnpm build
# Output in dist/
```

## Audit Trail

### Features

- **Tamper-Evident**: HMAC-SHA256 signatures on each entry
- **Hash Chain**: Each entry includes hash of previous entry
- **PII Handling**: Configurable mask/hash/drop for sensitive data
- **Export**: CSV and JSON export formats

### Audit Entry Structure

```json
{
  "id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z",
  "action": "create",
  "resource_type": "User",
  "resource_id": "uuid",
  "actor_id": "user_uuid",
  "org_id": "org_uuid",
  "changes": {"field": {"old": "x", "new": "y"}},
  "signature": "hmac_signature",
  "previous_hash": "hash_of_previous_entry"
}
```

### Verification

```bash
# Verify single entry
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"audit_id": "uuid"}' \
  http://localhost:8000/api/v1/audit/verify

# Verify chain integrity
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id": "uuid", "start_date": "2024-01-01"}' \
  http://localhost:8000/api/v1/audit/chain-verify
```

## Custom Webhooks

### Overview

Send HTTP callbacks when events occur in the system.

### Supported Events

- `user.created`, `user.updated`, `user.deleted`
- `org.created`, `org.updated`
- `team.created`, `team.updated`
- `membership.created`, `membership.updated`, `membership.deleted`

### Creating a Webhook

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/webhook",
    "events": ["user.created", "user.updated"],
    "secret": "your_signing_secret"
  }' \
  http://localhost:8000/api/v1/webhooks
```

### Webhook Payload

```json
{
  "event": "user.created",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

Webhooks include an `X-Webhook-Signature` header (HMAC-SHA256) for verification.

## Storage Configuration

### Local Storage (Default)

Files stored in `media/` directory.

### S3/MinIO Storage

```bash
USE_S3=true
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_ENDPOINT_URL=https://s3.amazonaws.com  # or MinIO URL
```

### MinIO (Local S3)

Included in Docker Compose:
- Console: http://localhost:9001 (minio/minio123)
- API: http://localhost:9000

## Runbooks

### Rotate Django Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Update DJANGO_SECRET_KEY and restart services
```

### Clear Redis Caches

```bash
docker compose -f compose/docker-compose.yml exec redis redis-cli FLUSHALL
```

### View Celery Logs

```bash
docker compose -f compose/docker-compose.yml logs -f celery
```

### Debug Failed Tasks (DLQ)

```bash
curl http://localhost:8000/api/v1/monitoring/queues | jq '.queues[] | select(.name == "dlq")'
```

### Run Migrations

```bash
docker compose -f compose/docker-compose.yml exec -w /app/backend web python manage.py migrate
```

## Architecture Overview

### Request/AuthZ Flow

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant KC as Keycloak
  participant API as Django/DRF
  participant CER as Cerbos
  participant DB as Postgres

  FE->>KC: OIDC login (or local auth)
  KC-->>FE: JWT (roles/claims)
  FE->>API: API call + Bearer JWT
  API->>CER: Principal/Resource check
  CER-->>API: Allow/Deny (+policy)
  API->>DB: Data access (if allowed)
  API-->>FE: 200/403 + audit log
```

### Key Files

| Path | Description |
|------|-------------|
| `backend/api/auth.py` | JWT authentication class |
| `backend/api/permissions.py` | Cerbos permission class |
| `backend/api/cerbos_client.py` | Cerbos client with caching |
| `backend/api/views_local_auth.py` | Local authentication endpoints |
| `backend/api/views_billing.py` | B2B billing endpoints |
| `backend/api/views_user_billing.py` | B2C billing endpoints |
| `backend/api/stripe_client.py` | Stripe SDK wrapper |
| `backend/api/audit.py` | Audit logging system |
| `policies/*.yaml` | Cerbos policy definitions |
| `frontend/src/routes/` | React admin pages |

## Testing

```bash
# Run all tests
docker compose -f compose/docker-compose.yml exec -w /app/backend web \
  pytest --cov=backend --cov-report=term-missing

# Run specific test file
pytest backend/api/tests/test_billing.py -v

# Run with coverage
pytest backend/ --cov=backend --cov-report=html
```

### Test Coverage

Current coverage: **77%+** (threshold: 75%)

### Test Categories

- **Unit Tests**: Models, serializers, utilities
- **Integration Tests**: API endpoints, auth flows
- **Policy Tests**: Cerbos RBAC/ABAC policies
- **Billing Tests**: Stripe integration, webhooks

## License

See LICENSE file.

## Related Documentation

- [PRD.md](PRD.md) - Full product requirements
- [Keycloak Admin](http://localhost:8080) - Keycloak console (admin/admin)
- [RabbitMQ Management](http://localhost:15672) - RabbitMQ console (guest/guest)
- [Mailpit](http://localhost:8025) - Email testing UI

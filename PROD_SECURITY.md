# Production Security & Hardening Plan

Actionable items to move from dev-friendly defaults to production-grade posture. Each item assumes `DJANGO_SETTINGS_MODULE=config.settings.production`.

**Legend:** ✅ Implemented | ⚠️ Partially implemented | ❌ Not implemented | 🔧 Needs configuration

---

## Transport & Identity

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| Cerbos TLS verification | ❌ | `api/cerbos_client.py:16` | **CRITICAL:** Currently hardcoded `tls_verify=False`. Must be `True` in production with proper CA bundle or mTLS. |
| Keycloak issuer validation | ✅ | `api/auth.py:140-145` | Multiple issuers allowed for dev; tighten to exact issuer in prod. |
| Keycloak audience validation | ✅ | `api/auth.py:157-163` | Validates `aud` or `azp` against `KEYCLOAK_AUDIENCE`. |
| Local JWT signing keys | ✅ | `api/local_jwt.py:77-78` | Fails in production if keys not configured; auto-generates in DEBUG only. |
| Local JWT audience validation | ⚠️ | `api/local_jwt.py:232-238` | **ISSUE:** `verify_token()` validates issuer but not audience. Add audience check. |
| Admin hostname restriction | ✅ | `config/middleware.py:69-114` | `AdminHostnameMiddleware` blocks `/admin` from non-admin hostnames. Set `ADMIN_HOSTNAME` env var. |

**Action Items:**

- [ ] Change `api/cerbos_client.py:16` to read TLS config from settings: `tls_verify=getattr(settings, 'CERBOS_TLS_VERIFY', not settings.DEBUG)`
- [ ] Add `CERBOS_TLS_VERIFY=true` and `CERBOS_CA_BUNDLE` settings for production
- [ ] Add audience validation to `api/local_jwt.py:verify_token()`

---

## Authorization Scope

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| Principal building | ✅ | `api/permissions.py` | Roles extracted from token claims. |
| Cerbos cache isolation | ⚠️ | `api/cerbos_client.py:49` | Uses `caches["default"]`. Should use isolated cache alias. |
| Cerbos cache invalidation | ⚠️ | `api/cerbos_client.py:84-86` | `invalidate_decision_cache()` clears entire default cache (coarse). |

**Action Items:**
- [ ] Add `cerbos` cache alias in settings with dedicated Redis DB or key prefix
- [ ] Implement targeted cache invalidation by principal/resource rather than full clear

---

## Access Keys (AKSK)

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| HMAC signature components | ⚠️ | `api/auth_access_key.py:145` | **ISSUE:** Only signs `timestamp + method + path`. Missing: host, query string, body hash. |
| Timestamp window | ✅ | `api/auth_access_key.py:27` | 5-minute tolerance (`AKSK_TIMESTAMP_TOLERANCE_SECONDS`). Consider shortening. |
| Replay protection | ❌ | — | No nonce/idempotency key to prevent replay within the timestamp window. |
| Secret encryption | ✅ | `api/models_access_keys.py` | Secrets use `EncryptedCharField`. |

**Action Items:**
- [ ] Update `compute_signature()` to include: `host + canonical_path + sorted_query_params + sha256(body)`
- [ ] Add nonce tracking in Redis with TTL matching timestamp window
- [ ] Shorten timestamp window to 60-120 seconds

---

## Impersonation

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| MFA requirement for admin | ❌ | `api/impersonation.py:20-33` | **CRITICAL:** `can_impersonate()` only checks `platform_admin` role, not MFA claims. |
| User creation during impersonation | ❌ | `api/impersonation.py:47` | **SECURITY ISSUE:** `get_impersonated_user()` uses `get_or_create()`, allowing user creation. |
| Audit logging | ✅ | `api/auth.py:90-100` | Logs impersonation start with admin/target IDs and request context. |
| Impersonation toggle | ✅ | `api/impersonation.py:100-107` | Controlled by `IMPERSONATION_ENABLED` setting. |

**Action Items:**
- [ ] Add MFA check to `can_impersonate()`:
  ```python
  def can_impersonate(claims: Dict[str, Any]) -> bool:
      # Check MFA verified
      acr = claims.get("acr", "")
      mfa_acr_values = getattr(settings, "MFA_ACR_VALUES", [...])
      if acr not in mfa_acr_values:
          return False
      # Check platform_admin role
      ...
  ```
- [ ] Change `get_impersonated_user()` to use `User.objects.get()` only (no creation)
- [ ] Add org membership verification for target user

---

## Throttling & Abuse

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| Per-org throttling | ✅ | `api/throttling.py:18-153` | `OrgRateThrottle` with tier-based limits. |
| Org ID spoofing | ⚠️ | `api/throttling.py:142` | **ISSUE:** Accepts `org_id` from query params, which could be spoofed. |
| Anonymous throttling | ✅ | `config/settings/base.py:162` | `AnonRateThrottle` at 100/hour. |
| User throttling | ✅ | `config/settings/base.py:163` | `UserRateThrottle` at 1000/hour. |
| Login rate limiting | ✅ | `api/views_local_auth.py:39-42` | 20/minute for login attempts. |
| Registration rate limiting | ✅ | `api/views_local_auth.py:33-36` | 10/hour for registration. |
| MFA rate limiting | ✅ | `api/throttling_mfa.py` | Rate limits MFA verification attempts. |

**Action Items:**
- [ ] Remove query param `org_id` acceptance in `OrgRateThrottle.get_org_id()`
- [ ] Only use `org_id` from authenticated token claims or verified membership

---

## Tokens & Sessions

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| Refresh token storage | ✅ | `api/models_local_auth.py:267` | Stored as SHA256 hash. |
| Refresh token rotation | ❌ | `api/views_local_auth.py:280-329` | **ISSUE:** `TokenRefreshView` does not rotate tokens on refresh. |
| Refresh token reuse detection | ❌ | — | No family tracking or reuse detection implemented. |
| Device binding | ⚠️ | `api/models_local_auth.py:233` | Stores `user_agent` and `ip_address` but doesn't enforce binding. |
| Email verification tokens | ⚠️ | `api/models_local_auth.py:47` | **ISSUE:** Stored as plaintext; should be hashed. Uses `secrets.compare_digest()` ✅. |
| Password reset tokens | ⚠️ | `api/models_local_auth.py:51` | **ISSUE:** Stored as plaintext; should be hashed. Uses `secrets.compare_digest()` ✅. Token cleared after use ✅. |
| Token expiration | ✅ | Multiple locations | Configurable TTLs for all token types. |
| MFA enforcement | ✅ | `api/mfa.py` | Middleware, decorator, and mixin available. |

**Action Items:**
- [ ] Implement refresh token rotation in `TokenRefreshView`:
  ```python
  # Revoke old token, issue new refresh token
  old_token.revoke()
  new_refresh = generate_refresh_token(user)
  RefreshToken.create_for_user(user, new_refresh, ...)
  ```
- [ ] Add token family tracking for reuse detection
- [ ] Hash email verification and password reset tokens before storage

---

## Settings & Secrets

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| SECRET_KEY validation | ✅ | `config/settings/production.py:17-18` | Fails if default "changeme" is used. |
| DEBUG enforcement | ✅ | `config/settings/production.py:14` | Hardcoded `DEBUG = False`. |
| CSP configuration | ✅ | `config/settings/base.py:186-195` | Base CSP defined; production removes `unsafe-inline` for styles. |
| CORS configuration | 🔧 | `config/settings/base.py:181-182` | Set `CORS_ALLOWED_ORIGINS` env var to explicit origins. |
| Field encryption keys | 🔧 | `config/settings/base.py:447-454` | Warning if not set; raises in encryption operations. |
| Audit signing key | 🔧 | `config/settings/base.py:458-469` | Warning if not set; logs are unsigned without it. |
| Local auth toggle | ✅ | `config/settings/base.py:473` | `LOCAL_AUTH_ENABLED` setting. |

**Action Items:**
- [ ] Set all required environment variables in production (see `.env.example`)
- [ ] Use a secrets manager (AWS Secrets Manager, Vault, etc.) for sensitive values

---

## Data Protection

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| S3/MinIO storage | 🔧 | `config/settings/base.py:197-215` | Configure when `USE_S3=true`. |
| Field-level encryption | ✅ | `api/encryption.py` | `EncryptedCharField`, `EncryptedTextField`, `EncryptedJSONField` available. |
| Key rotation support | ✅ | `api/encryption.py:121-146` | `MultiFernet` supports decrypting with old keys. |
| Access key secret encryption | ✅ | `api/models_access_keys.py` | Uses `EncryptedCharField`. |

---

## Observability & Compliance

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| Sentry integration | ✅ | `config/settings/base.py:258-267` | `send_default_pii=False` for privacy. |
| Structured logging | ✅ | `config/settings/base.py:225-242` | Structlog with PII redaction. |
| Audit log signing | ✅ | `api/audit_integrity.py` | HMAC-SHA256 signatures with chain linking. |
| Audit chain verification | ✅ | `api/audit_integrity.py:241-339` | `verify_chain_integrity()` function. |
| Request ID tracking | ✅ | `config/middleware.py:11-66` | `RequestIDMiddleware` with metrics. |

---

## Deployment & Network

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| HTTPS redirect | ✅ | `config/settings/production.py:21` | `SECURE_SSL_REDIRECT = True`. |
| HSTS | ✅ | `config/settings/production.py:24-27` | 1-year max-age with preload. |
| Secure cookies | ✅ | `config/settings/production.py:29-36` | Session and CSRF cookies are `Secure`, `HttpOnly`, `SameSite=Lax`. |
| Proxy headers | ✅ | `config/settings/production.py:22` | `SECURE_PROXY_SSL_HEADER` configured. |
| X-Frame-Options | ✅ | `config/settings/production.py:41` | `DENY`. |
| XSS filter | ✅ | `config/settings/production.py:39` | Browser XSS filter enabled. |
| Content type sniffing | ✅ | `config/settings/production.py:40` | `X-Content-Type-Options: nosniff`. |

---

## Frontend (React Admin)

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| HTTPS enforcement | 🔧 | `frontend/.env.example` | Set `VITE_API_URL` and `VITE_KEYCLOAK_URL` to HTTPS. |
| Token storage | ⚠️ | `frontend/src/lib/auth/local-storage.ts` | Uses `sessionStorage`. Consider httpOnly cookies for higher security. |
| OIDC PKCE | ⚠️ | `frontend/src/lib/auth/oidc-config.ts` | Uses `response_type: "code"` but PKCE not explicitly enabled. oidc-client-ts enables PKCE by default for code flow. |
| OIDC session storage | ✅ | `frontend/src/lib/auth/oidc-config.ts:16` | Uses `sessionStorage` via `WebStorageStateStore`. |
| WebSocket token in query string | ⚠️ | `frontend/src/lib/websocket/ws-client.ts:54` | **ISSUE:** Token in URL can leak to server logs. Move to subprotocol or short-lived ticket. |
| Route guards | ✅ | `frontend/src/routes/*/\_layout.tsx` | Auth checks in route layouts. |
| XSS prevention | ✅ | React + no `dangerouslySetInnerHTML` usage | React escapes by default; no dangerous HTML rendering found. |
| Source maps in production | ⚠️ | `frontend/vite.config.ts` | **ISSUE:** No explicit `build.sourcemap: false`. Vite defaults to no source maps, but should be explicit. |

**Action Items:**
- [ ] Add to `vite.config.ts`:
  ```ts
  build: {
    sourcemap: false,
  }
  ```
- [ ] Implement WebSocket authentication via subprotocol or short-lived signed ticket instead of query param
- [ ] Consider using httpOnly cookies via BFF pattern for token storage

---

## Additional Security Considerations

### Database Security
- [ ] Enable SSL for PostgreSQL connections in production
- [ ] Use separate database users with minimal privileges
- [ ] Enable query logging for audit purposes

### Redis Security
- [ ] Enable Redis AUTH
- [ ] Use TLS for Redis connections
- [ ] Consider Redis ACLs for multi-tenant isolation

### Celery Security
- [ ] Enable message signing between workers and broker
- [ ] Monitor dead letter queue for failed tasks
- [ ] Set appropriate task time limits

### Container Security
- [ ] Run containers as non-root user
- [ ] Use read-only root filesystem where possible
- [ ] Implement resource limits (CPU, memory)
- [ ] Scan images for vulnerabilities in CI

---

## Quick Reference: Environment Variables

```bash
# Required for production
DJANGO_SECRET_KEY=<generate-secure-key>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=your-domain.com

# Authentication
KEYCLOAK_SERVER_URL=https://keycloak.your-domain.com
LOCAL_AUTH_PRIVATE_KEY=<rsa-private-key>
LOCAL_AUTH_PUBLIC_KEY=<rsa-public-key>

# Security
ADMIN_HOSTNAME=admin.your-domain.com
FIELD_ENCRYPTION_KEYS=<fernet-key-1>,<fernet-key-2>
AUDIT_SIGNING_KEY=<hex-signing-key>
CERBOS_TLS_VERIFY=true

# External services
CORS_ALLOWED_ORIGINS=https://your-frontend.com
SENTRY_DSN=<your-sentry-dsn>
```

---

## Checklist Summary

**Critical (must fix before production):**
- [ ] Cerbos TLS verification (`api/cerbos_client.py:16`)
- [ ] Impersonation MFA requirement (`api/impersonation.py`)
- [ ] Impersonation user creation (`api/impersonation.py:47`)

**High Priority:**
- [ ] Refresh token rotation
- [ ] AKSK signature strengthening
- [ ] Org ID spoofing in throttling
- [ ] Hash email/password reset tokens

**Medium Priority:**
- [ ] Local JWT audience validation
- [ ] Cerbos cache isolation
- [ ] WebSocket token handling
- [ ] Explicit source map disabling

**Configuration Required:**
- [ ] All environment variables set
- [ ] CORS origins configured
- [ ] Encryption keys generated and stored securely

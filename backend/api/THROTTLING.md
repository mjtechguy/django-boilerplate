# Per-Tenant Rate Limiting

This document describes the per-organization (tenant) rate limiting implementation.

## Overview

The system implements organization-scoped throttling to:
- Prevent any single tenant from consuming all API resources
- Enforce API quotas based on license tier
- Provide fair usage across all tenants

## How It Works

### Rate Limit Hierarchy

Rate limits are determined in the following order of precedence:

1. **Custom org feature flags** - `org.feature_flags['api_rate_limit']`
2. **License tier defaults** - From `STRIPE_TIER_FEATURES` in settings
3. **Free tier default** - 100 requests/hour

### License Tier Defaults

| Tier       | Rate Limit       | Notes                          |
|------------|------------------|--------------------------------|
| Free       | 100/hour         | Default for new organizations  |
| Starter    | 1000/hour        |                                |
| Pro        | 10000/hour       |                                |
| Enterprise | Unlimited (-1)   | No rate limiting applied       |

### Organization ID Extraction

The throttle extracts `org_id` from requests using this fallback chain:

1. `request.token_claims['org_id']` - From JWT token (most reliable)
2. `request.query_params.get('org_id')` - Query parameter
3. `request.user.memberships.first().org_id` - User's first membership

If no `org_id` is found, org-level throttling is skipped (falls back to user/anon throttling).

## Configuration

### Settings

The throttle is registered in `config/settings/base.py`:

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "api.throttling.OrgRateThrottle",  # Per-tenant throttling
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "org": "1000/hour",  # Default, overridden per org
    },
}
```

### Redis Cache

The throttle uses the `idempotency` cache (Redis DB 1) to store request counts:

```python
CACHES = {
    "idempotency": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        ...
    },
}
```

Cache keys follow the format: `throttle:org:{org_id}:requests`

## Custom Rate Limits

### Via Feature Flags

You can set a custom rate limit for any organization:

```python
org = Org.objects.get(id=org_id)
org.feature_flags = {"api_rate_limit": 500}  # 500 requests/hour
org.save()
```

### Unlimited Access

Set rate limit to `-1` for unlimited access:

```python
org.feature_flags = {"api_rate_limit": -1}
org.save()
```

## API Responses

### Success Response

When a request is allowed:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

### Throttled Response

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

## Checking Rate Limit Status

Use the `get_org_rate_limit_status()` utility function:

```python
from api.throttling import get_org_rate_limit_status

status = get_org_rate_limit_status(org_id)
# Returns:
# {
#     "limit": 100,           # Max requests per hour (-1 for unlimited)
#     "remaining": 95,        # Requests remaining in current window
#     "reset_at": 1234567890  # Unix timestamp when limit resets
# }
```

## Testing

Run the throttling tests:

```bash
pytest backend/api/tests/test_throttling.py -v
```

Test coverage includes:
- Free tier (100/hour)
- Starter tier (1000/hour)
- Pro tier (10000/hour)
- Enterprise tier (unlimited)
- Custom rate limits via feature_flags
- Independent limits per organization
- Requests without org_id

## Implementation Details

### Class: `OrgRateThrottle`

Located in `backend/api/throttling.py`

**Key Methods:**

- `get_cache_key(request, view)` - Generates org-scoped cache key
- `get_rate()` - Determines rate limit for current org
- `get_org_id(request)` - Extracts org_id from request
- `get_rate_from_settings()` - Falls back to Django settings

**Inheritance:**

Extends `rest_framework.throttling.SimpleRateThrottle`, which provides:
- Request history tracking
- Time window calculations
- Automatic cache cleanup

### Cache Storage

DRF's `SimpleRateThrottle` stores a list of request timestamps in Redis:

```python
# Cache structure (simplified)
{
    "throttle:org:uuid-123:requests": [
        1234567890.123,  # Timestamp of request 1
        1234567891.456,  # Timestamp of request 2
        1234567892.789,  # Timestamp of request 3
        ...
    ]
}
```

Old timestamps outside the time window are automatically removed.

## Migration from Global Throttling

The new org-level throttling **supplements** (not replaces) existing throttling:

1. Anonymous requests: Still limited by `AnonRateThrottle`
2. Authenticated users: Limited by **both** `UserRateThrottle` AND `OrgRateThrottle`
3. Requests without org: Limited by `UserRateThrottle` only

This means:
- A user can't exceed their personal rate limit even if org limit is higher
- An org can't exceed its org limit even if user limit is higher
- Both limits are enforced independently

## Monitoring

### Metrics to Track

1. **Throttle events** - Count of 429 responses per org
2. **Rate limit usage** - % of limit used per org
3. **Org distribution** - Which orgs hit limits most often

### Log Example

When throttling occurs:

```json
{
  "message": "Request throttled",
  "org_id": "uuid-123",
  "license_tier": "free",
  "rate_limit": 100,
  "status_code": 429,
  "path": "/api/v1/resources",
  "method": "GET"
}
```

## Troubleshooting

### Issue: Rate limit not enforced

**Check:**
1. Is `OrgRateThrottle` in `DEFAULT_THROTTLE_CLASSES`?
2. Is Redis running and accessible?
3. Does the request have an `org_id`?

**Debug:**
```python
from api.throttling import OrgRateThrottle
throttle = OrgRateThrottle()
org_id = throttle.get_org_id(request)
rate = throttle.get_rate()
print(f"org_id: {org_id}, rate: {rate}")
```

### Issue: Wrong rate limit applied

**Check:**
1. Org's `license_tier` field
2. Org's `feature_flags` for custom `api_rate_limit`
3. `STRIPE_TIER_FEATURES` in settings

**Debug:**
```python
org = Org.objects.get(id=org_id)
print(f"Tier: {org.license_tier}")
print(f"Flags: {org.feature_flags}")
```

### Issue: Cache not clearing

**Clear manually:**
```python
from django.core.cache import caches
cache = caches["idempotency"]
cache.delete_pattern("throttle:org:*")
```

---

# API Key Creation Limits

This document also describes the rate limiting and quota enforcement for API key creation.

## Overview

The system implements two types of limits for API key creation to prevent abuse:

1. **Rate Limiting** - Limits how quickly a user can create API keys (e.g., 5 per hour)
2. **Quotas** - Limits the total number of active API keys per user based on org tier

These limits prevent:
- Resource exhaustion attacks through unlimited key creation
- Key proliferation that complicates security audits
- Database overload from malicious users

## Rate Limiting

### How It Works

The `APIKeyCreationThrottle` class limits the rate at which any user can create API keys:

- **Default Rate**: 5 API key creation attempts per hour
- **Configurable**: Set via `THROTTLE_RATE_API_KEY_CREATE` environment variable
- **Per-User**: Each user has an independent rate limit
- **All Attempts Count**: Both successful and failed creation attempts count toward the limit
- **Unauthenticated Bypass**: Unauthenticated requests are not throttled

### Configuration

Add to your environment variables:

```bash
# .env
THROTTLE_RATE_API_KEY_CREATE=5/hour
```

The throttle is automatically applied to the `UserAPIKeyCreateView` in `backend/api/views_api_keys.py`:

```python
class UserAPIKeyCreateView(APIView):
    throttle_classes = [APIKeyCreationThrottle]
    ...
```

### Throttled Response

When the rate limit is exceeded, users receive a 429 response:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

### Cache Storage

The throttle uses the default cache (Redis DB 0) with keys in the format:

```
throttle:apikey:create:user:{user_id}
```

Request timestamps are stored for the duration of the time window (e.g., 1 hour).

## API Key Quotas

### How It Works

Quotas limit the total number of **active** (non-revoked) API keys a user can have:

- **Tier-Based**: Different limits based on organization's license tier
- **Revoked Keys Excluded**: Only active keys count toward quota
- **Pre-Creation Check**: Quota is checked before key creation (efficient)
- **Custom Overrides**: Can be customized per org via feature flags

### Tier-Based Quotas

| Tier       | Max API Keys | Notes                          |
|------------|--------------|--------------------------------|
| Free       | 5            | Default for users without org  |
| Starter    | 10           |                                |
| Pro        | 25           |                                |
| Enterprise | Unlimited    | Returns -1 (no quota limit)    |

### Quota Response

#### API Key List Response

The `UserAPIKeyListView` includes quota information:

```http
GET /api/v1/api-keys/

HTTP/1.1 200 OK
Content-Type: application/json

{
  "keys": [...],
  "active_keys": 3,
  "max_keys": 5,
  "remaining": 2
}
```

#### API Key Creation Response

The `UserAPIKeyCreateView` also includes quota information:

```http
POST /api/v1/api-keys/

HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "uuid-123",
  "name": "My API Key",
  "key": "sk_...",
  "created_at": "2026-01-04T19:00:00Z",
  "active_keys": 4,
  "max_keys": 5,
  "remaining": 1
}
```

### Quota Exceeded Response

When quota is exceeded:

```http
POST /api/v1/api-keys/

HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "API key quota exceeded. You have 5 active keys and your limit is 5. Please revoke unused keys before creating new ones."
}
```

### Custom Quota Overrides

Set custom quota for any organization via feature flags:

```python
org = Org.objects.get(id=org_id)
org.feature_flags = {"max_api_keys": 50}  # Custom limit
org.save()
```

For unlimited quota:

```python
org.feature_flags = {"max_api_keys": -1}  # Unlimited
org.save()
```

## Configuration in Settings

### STRIPE_TIER_FEATURES

API key quotas are configured in `backend/config/settings/base.py`:

```python
STRIPE_TIER_FEATURES = {
    "free": {
        "api_rate_limit": 100,
        "max_api_keys": 5,  # ← API key quota
        ...
    },
    "starter": {
        "api_rate_limit": 1000,
        "max_api_keys": 10,  # ← API key quota
        ...
    },
    "pro": {
        "api_rate_limit": 10000,
        "max_api_keys": 25,  # ← API key quota
        ...
    },
    "enterprise": {
        "api_rate_limit": -1,
        "max_api_keys": -1,  # ← Unlimited
        ...
    },
}
```

### Throttle Rates

In the same settings file:

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "org": "1000/hour",
        "api_key_create": "5/hour",  # ← API key creation throttle
    },
}
```

## Checking Quota Status

Use the `get_user_api_key_quota()` utility function:

```python
from api.throttling_api_keys import get_user_api_key_quota

max_keys = get_user_api_key_quota(request.user)
# Returns:
# - Positive integer: Maximum allowed API keys
# - -1: Unlimited (enterprise tier)
```

Get current usage:

```python
from api.models import UserAPIKey

active_keys = UserAPIKey.objects.filter(
    user=request.user,
    revoked_at__isnull=True
).count()

remaining = max_keys - active_keys if max_keys != -1 else -1
```

## Testing

### Quota Tests

Run quota enforcement tests:

```bash
pytest backend/api/tests/test_api_keys.py::test_api_key_quota -v
```

Test coverage includes:
- Quota limits for all tiers (free, starter, pro, enterprise)
- 403 response when quota exceeded
- Revoked keys don't count against quota
- Feature flag custom quota overrides
- Quota info in list and create responses

### Throttle Tests

Run API key creation throttling tests:

```bash
pytest backend/api/tests/test_throttling_api_keys.py -v
```

Test coverage includes:
- Rate limiting allows configured requests before blocking
- 429 response when rate limit exceeded
- Throttle reset after time window
- Per-user independent throttling
- Interaction between throttle and quota limits

## Implementation Details

### Class: `APIKeyCreationThrottle`

Located in `backend/api/throttling_api_keys.py`

**Key Methods:**

- `allow_request(request, view)` - Check if request should be allowed
- `wait()` - Calculate wait time until next allowed request
- `get_rate()` - Get throttle rate from settings
- `parse_rate(rate)` - Parse rate string to (num_requests, duration)

**Inheritance:**

Extends `rest_framework.throttling.BaseThrottle` with custom implementation for per-user API key creation throttling.

### Function: `get_user_api_key_quota(user)`

Located in `backend/api/throttling_api_keys.py`

**Algorithm:**

1. Get user's organization from first membership
2. Check `org.feature_flags['max_api_keys']` for custom override
3. Fall back to `STRIPE_TIER_FEATURES[tier]['max_api_keys']`
4. Default to free tier limit (5) if no org found

**Returns:**

- Positive integer for quota limit
- `-1` for unlimited (enterprise tier)

## Interaction with Other Limits

API key creation is subject to **multiple layers** of limiting:

1. **Global User Rate Limit** - `UserRateThrottle` (1000/hour default)
2. **Org Rate Limit** - `OrgRateThrottle` (tier-based, see above)
3. **API Key Creation Rate Limit** - `APIKeyCreationThrottle` (5/hour default)
4. **API Key Quota** - Per-tier max active keys (5-25 or unlimited)

**All limits are enforced independently.** The most restrictive limit applies.

Example: A user in a Pro org can make 10,000 requests/hour (org limit), but can only create 5 API keys per hour (creation throttle) and can have at most 25 active keys (quota).

## Troubleshooting

### Issue: Can't create API keys despite being under quota

**Check:**
1. Are you hitting the rate limit (5/hour)?
2. Check last 5 creation attempts' timestamps
3. Wait for the throttle window to reset

**Debug:**
```python
from api.throttling_api_keys import APIKeyCreationThrottle
from django.core.cache import caches

cache = caches["default"]
key = f"throttle:apikey:create:user:{user.id}"
history = cache.get(key, [])
print(f"Requests in last hour: {len(history)}")
```

### Issue: Quota limit seems wrong

**Check:**
1. User's org `license_tier`
2. Org's `feature_flags` for custom `max_api_keys`
3. `STRIPE_TIER_FEATURES` in settings

**Debug:**
```python
from api.throttling_api_keys import get_user_api_key_quota

max_keys = get_user_api_key_quota(request.user)
print(f"Max API keys: {max_keys}")

org = request.user.memberships.first().org
print(f"Tier: {org.license_tier}")
print(f"Feature flags: {org.feature_flags}")
```

### Issue: Need to reset throttle for a user

**Clear throttle cache:**
```python
from django.core.cache import caches

cache = caches["default"]
cache.delete(f"throttle:apikey:create:user:{user.id}")
```

## Monitoring

### Metrics to Track

1. **Quota usage** - % of quota used per user/tier
2. **Throttle hits** - Count of 429 responses for API key creation
3. **Quota exhaustion** - Count of 403 responses (quota exceeded)
4. **Keys per user** - Distribution of active keys per user

### Log Examples

When quota exceeded:

```json
{
  "message": "API key quota exceeded",
  "user_id": "uuid-123",
  "active_keys": 5,
  "max_keys": 5,
  "status_code": 403
}
```

When throttled:

```json
{
  "message": "API key creation throttled",
  "user_id": "uuid-123",
  "status_code": 429,
  "retry_after": 3600
}
```

---

## Future Enhancements

Potential improvements:

1. **Per-endpoint limits** - Different limits for expensive operations
2. **Burst allowance** - Allow short bursts above sustained rate
3. **Rate limit headers** - Add `X-RateLimit-*` headers to all responses
4. **Admin dashboard** - UI to view/modify org rate limits
5. **Alerts** - Notify admins when org approaches limit
6. **Analytics** - Track usage patterns per org/tier

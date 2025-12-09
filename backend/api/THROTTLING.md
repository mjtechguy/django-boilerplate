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

## Future Enhancements

Potential improvements:

1. **Per-endpoint limits** - Different limits for expensive operations
2. **Burst allowance** - Allow short bursts above sustained rate
3. **Rate limit headers** - Add `X-RateLimit-*` headers to all responses
4. **Admin dashboard** - UI to view/modify org rate limits
5. **Alerts** - Notify admins when org approaches limit
6. **Analytics** - Track usage patterns per org/tier

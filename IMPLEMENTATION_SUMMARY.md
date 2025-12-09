# Per-Tenant Rate Limiting Implementation Summary

## Overview

Implemented per-organization rate limiting to prevent any single tenant from consuming all API resources and to enforce API quotas based on license tier.

## Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Request                               │
│                     (with Bearer Token)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ Authentication │
                    │   (HybridJWT)  │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ Extract org_id │
                    │  from claims   │
                    └────────┬───────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ AnonThrottle │    │ UserThrottle │    │  OrgThrottle │
│  (100/hour)  │    │ (1000/hour)  │    │ (tier-based) │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       │                   │                    ▼
       │                   │            ┌───────────────┐
       │                   │            │  Get org from │
       │                   │            │    database   │
       │                   │            └───────┬───────┘
       │                   │                    │
       │                   │                    ▼
       │                   │            ┌───────────────┐
       │                   │            │  Check rate:  │
       │                   │            │ feature_flags │
       │                   │            │   or tier     │
       │                   │            └───────┬───────┘
       │                   │                    │
       │                   │                    ▼
       │                   │          ┌──────────────────┐
       │                   │          │ Redis: Get count │
       │                   │          │ throttle:org:id  │
       │                   │          └────────┬─────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
     ┌──────────┐                  ┌──────────┐
     │  Allow   │                  │ Throttle │
     │ 200 OK   │                  │ 429 Error│
     └──────────┘                  └──────────┘
```

## Files Created/Modified

### Created Files

1. **`backend/api/throttling.py`** (132 lines)
   - `OrgRateThrottle` class - DRF throttle that enforces per-org limits
   - `get_org_rate_limit_status()` - Utility function for checking rate limit status

2. **`backend/api/tests/test_throttling.py`** (272 lines)
   - Comprehensive test suite for throttling functionality
   - Tests all tier limits (free, starter, pro, enterprise)
   - Tests custom rate limits via feature_flags
   - Tests independent limits per organization

3. **`backend/api/THROTTLING.md`** (Documentation)
   - Complete documentation of the throttling system
   - Configuration guide
   - API examples
   - Troubleshooting guide

### Modified Files

1. **`backend/config/settings/base.py`**
   - Added `api.throttling.OrgRateThrottle` to `DEFAULT_THROTTLE_CLASSES`
   - Added `"org": "1000/hour"` to `DEFAULT_THROTTLE_RATES`
   - Updated pro tier `api_rate_limit` from 5000 to 10000 (as per requirements)

2. **`README.md`**
   - Updated rate limiting feature description to mention tier-based quotas

## How It Works

### Rate Limit Hierarchy

Rate limits are determined by (in order of precedence):

1. **Custom org feature flags** - `org.feature_flags['api_rate_limit']`
2. **License tier defaults** - From `STRIPE_TIER_FEATURES`
3. **Free tier default** - 100 requests/hour

### Tier Defaults

| Tier       | Rate Limit       |
|------------|------------------|
| Free       | 100/hour         |
| Starter    | 1000/hour        |
| Pro        | 10000/hour       |
| Enterprise | Unlimited (-1)   |

### Organization ID Extraction

The throttle extracts `org_id` from requests using this fallback chain:

1. `request.token_claims['org_id']` - From JWT token (most reliable)
2. `request.query_params.get('org_id')` - Query parameter
3. `request.user.memberships.first().org_id` - User's first membership

If no `org_id` is found, org-level throttling is skipped.

### Redis Storage

- Uses the `idempotency` Redis cache (DB 1)
- Cache keys: `throttle:org:{org_id}:requests`
- Stores list of request timestamps
- Automatic cleanup of old timestamps

## Key Features

1. **Per-organization isolation** - Each org has independent rate limits
2. **Tier-based quotas** - Limits automatically adjust with license tier changes
3. **Custom overrides** - Orgs can have custom limits via feature_flags
4. **Unlimited access** - Enterprise tier (or custom -1) disables throttling
5. **Graceful fallback** - Missing org_id falls back to user-level throttling
6. **Standard responses** - Returns 429 with retry-after when throttled

## Testing

Run tests with:

```bash
pytest backend/api/tests/test_throttling.py -v
```

Test coverage includes:
- All tier limits (free, starter, pro, enterprise)
- Custom rate limits
- Independent limits per org
- Requests without org_id
- Multiple orgs simultaneously

## Usage Examples

### Setting Custom Rate Limit

```python
org = Org.objects.get(id=org_id)
org.feature_flags = {"api_rate_limit": 500}
org.save()
```

### Unlimited Access

```python
org.feature_flags = {"api_rate_limit": -1}
org.save()
```

### Check Rate Limit Status

```python
from api.throttling import get_org_rate_limit_status

status = get_org_rate_limit_status(org_id)
# Returns: {"limit": 100, "remaining": 95, "reset_at": timestamp}
```

## API Behavior

### Successful Request

```http
HTTP/1.1 200 OK
```

### Throttled Request

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600

{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

## Implementation Details

- **Class**: `OrgRateThrottle` extends `rest_framework.throttling.SimpleRateThrottle`
- **Scope**: `"org"`
- **Cache format**: `"throttle:org:%(ident)s:requests"`
- **Time window**: 1 hour (3600 seconds)

## Integration

The throttle is automatically applied to all API endpoints via `DEFAULT_THROTTLE_CLASSES`. It works alongside existing throttles:

1. `AnonRateThrottle` - For anonymous requests
2. `UserRateThrottle` - For authenticated users
3. `OrgRateThrottle` - For organization-scoped limits (NEW)

All three throttles are checked independently, so the most restrictive limit applies.

## Compliance with Requirements

- ✅ Extracts org_id from authenticated user's token claims or request
- ✅ Uses Redis to track request counts per org
- ✅ Reads rate limits from org's feature_flags or falls back to tier defaults
- ✅ Tier defaults from `STRIPE_TIER_FEATURES`:
  - free: 100 requests/hour
  - starter: 1000 requests/hour
  - pro: 10000 requests/hour
  - enterprise: unlimited (-1)
- ✅ Rate limit per hour matching existing global throttle format
- ✅ Returns 429 responses when limit exceeded
- ✅ Clean, minimal implementation
- ✅ Follows existing patterns in the codebase
- ✅ Comprehensive tests included

## Future Enhancements

Potential improvements for future iterations:

1. Per-endpoint rate limits (different limits for expensive operations)
2. Burst allowance (allow short bursts above sustained rate)
3. Rate limit headers in responses (`X-RateLimit-*`)
4. Admin dashboard UI for viewing/modifying org rate limits
5. Alerts when org approaches limit
6. Usage analytics and reporting

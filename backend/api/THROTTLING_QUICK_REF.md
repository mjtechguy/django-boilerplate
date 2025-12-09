# Per-Tenant Rate Limiting - Quick Reference

## Tier Limits

| Tier       | Limit/Hour | Override Example |
|------------|------------|------------------|
| Free       | 100        | `org.feature_flags = {"api_rate_limit": 50}` |
| Starter    | 1000       | `org.feature_flags = {"api_rate_limit": 500}` |
| Pro        | 10000      | `org.feature_flags = {"api_rate_limit": 5000}` |
| Enterprise | Unlimited  | Already unlimited |

## Common Operations

### Set Custom Limit
```python
from api.models import Org

org = Org.objects.get(id=org_id)
org.feature_flags = {"api_rate_limit": 500}  # 500/hour
org.save()
```

### Set Unlimited
```python
org.feature_flags = {"api_rate_limit": -1}
org.save()
```

### Remove Custom Limit (Use Tier Default)
```python
if "api_rate_limit" in org.feature_flags:
    del org.feature_flags["api_rate_limit"]
    org.save()
```

### Check Current Limit
```python
from api.throttling import get_org_rate_limit_status

status = get_org_rate_limit_status(org_id)
print(f"Limit: {status['limit']}, Remaining: {status['remaining']}")
```

## Cache Management

### View Cache Keys
```python
from django.core.cache import caches
cache = caches["idempotency"]
keys = cache.keys("throttle:org:*")
print(list(keys))
```

### Clear Org's Rate Limit
```python
cache_key = f"throttle:org:{org_id}:requests"
cache.delete(cache_key)
```

### Clear All Rate Limits
```python
cache.delete_pattern("throttle:org:*")
```

## Testing

### Run Throttle Tests
```bash
pytest backend/api/tests/test_throttling.py -v
```

### Test Specific Tier
```bash
pytest backend/api/tests/test_throttling.py::test_free_tier_rate_limit -v
```

## Debugging

### Check if Throttle is Active
```python
from django.conf import settings
print(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"])
# Should include 'api.throttling.OrgRateThrottle'
```

### Debug Org ID Extraction
```python
from api.throttling import OrgRateThrottle
from django.test import RequestFactory

factory = RequestFactory()
request = factory.get('/api/v1/test')
request.token_claims = {"org_id": "uuid-123"}

throttle = OrgRateThrottle()
org_id = throttle.get_org_id(request)
print(f"Extracted org_id: {org_id}")
```

### Debug Rate Calculation
```python
throttle = OrgRateThrottle()
throttle.org_id = org_id
rate = throttle.get_rate()
print(f"Rate for org {org_id}: {rate}")
```

## Response Headers

When throttled, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600

{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

## Environment Variables

None required. Rate limits are configured via:
1. Database (Org model)
2. Settings (STRIPE_TIER_FEATURES)

## Redis Database

- **Cache**: `idempotency` (Redis DB 1)
- **Keys**: `throttle:org:{org_id}:requests`
- **TTL**: 3600 seconds (1 hour)

## Files

- Implementation: `backend/api/throttling.py`
- Tests: `backend/api/tests/test_throttling.py`
- Settings: `backend/config/settings/base.py`
- Docs: `backend/api/THROTTLING.md`

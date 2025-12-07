# WebSocket Implementation Summary

This document summarizes the WebSocket implementation added to the Django boilerplate using Django Channels.

## Files Created/Modified

### New Files Created

1. **`/src/api/consumers.py`** (246 lines)
   - `NotificationConsumer` - Handles user-specific notifications
   - `OrganizationEventsConsumer` - Handles organization-wide events
   - `broadcast_notification()` - Helper to send notifications to users
   - `broadcast_org_event()` - Helper to broadcast events to organization members

2. **`/src/api/middleware.py`** (93 lines)
   - `JWTAuthMiddleware` - WebSocket authentication middleware
   - Extracts JWT from query string or Authorization header
   - Validates tokens using Keycloak (same as REST API)
   - Sets `scope["user"]` and `scope["token_claims"]`

3. **`/src/api/routing.py`** (14 lines)
   - WebSocket URL patterns configuration
   - Routes for `/ws/notifications/` and `/ws/events/<org_id>/`

4. **`/src/api/tests/test_websockets.py`** (510+ lines)
   - Comprehensive test suite using `channels.testing`
   - Tests authentication (valid/invalid tokens, headers, query strings)
   - Tests both consumer types with various scenarios
   - Tests message broadcasting and isolation
   - Tests organization membership verification
   - Tests ping/pong keep-alive mechanism

5. **`/src/api/websocket_signals.py`** (143 lines)
   - Example integration with Django signals
   - Signal handlers for automatic WebSocket broadcasting
   - Helper functions for common notification patterns
   - Demonstrates best practices for async/sync integration

6. **`/WEBSOCKET_USAGE.md`** (Documentation)
   - Complete usage guide for developers
   - Connection examples (JavaScript/React)
   - Broadcasting examples (Python/Django)
   - Production deployment instructions
   - Architecture overview

### Modified Files

1. **`/requirements.txt`**
   - Added `channels[daphne]==4.0.0`
   - Added `channels-redis==4.2.0`

2. **`/src/config/settings/base.py`**
   - Added `"daphne"` to `INSTALLED_APPS` (must be first)
   - Added `ASGI_APPLICATION = "config.asgi.application"`
   - Added `CHANNEL_LAYERS` configuration with Redis backend

3. **`/src/config/settings/test.py`**
   - Added `CHANNEL_LAYERS` with `InMemoryChannelLayer` for testing
   - No Redis required for tests

4. **`/src/config/asgi.py`**
   - Complete rewrite for WebSocket support
   - Added `ProtocolTypeRouter` for HTTP/WebSocket routing
   - Added `AllowedHostsOriginValidator` for security
   - Added `JWTAuthMiddleware` for authentication
   - Added `URLRouter` with WebSocket URL patterns

## Features Implemented

### 1. User Notifications (NotificationConsumer)

**Endpoint:** `ws://localhost:8000/ws/notifications/`

**Features:**
- JWT authentication required (query string or header)
- Each user joins their own notification channel
- Real-time notification delivery to specific users
- Ping/pong keep-alive support
- Automatic disconnection handling

**Use Cases:**
- Task completion notifications
- System alerts
- Direct messages
- Activity updates

### 2. Organization Events (OrganizationEventsConsumer)

**Endpoint:** `ws://localhost:8000/ws/events/<org_id>/`

**Features:**
- JWT authentication + organization membership verification
- Organization-scoped channel groups
- Real-time event broadcasting to all org members
- Membership validation on connect
- Isolated event streams per organization

**Use Cases:**
- Real-time collaboration updates
- Resource creation/modification notifications
- Member activity tracking
- Organization-wide announcements

### 3. Security Features

- **JWT Authentication:** All connections validated via Keycloak
- **Origin Validation:** `AllowedHostsOriginValidator` prevents CSRF
- **Membership Verification:** Org events require membership
- **Message Isolation:** Users only receive authorized messages
- **Channel Groups:** Isolated groups prevent cross-contamination

### 4. Broadcasting Helpers

**Async Functions:**
```python
await broadcast_notification(user_id, notification_dict)
await broadcast_org_event(org_id, event_type, data_dict)
```

**Sync Wrappers (for Celery/Signals):**
```python
async_to_sync(broadcast_notification)(user_id, notification_dict)
async_to_sync(broadcast_org_event)(org_id, event_type, data_dict)
```

## Architecture

```
┌─────────────────┐
│   WebSocket     │
│   Client        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ASGI Server    │
│  (Daphne)       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  ProtocolTypeRouter             │
│  ├─ "http" → Django ASGI        │
│  └─ "websocket" → Channels      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  AllowedHostsOriginValidator    │
│  (Security: Origin checking)    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  JWTAuthMiddleware              │
│  (Keycloak token validation)    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  URLRouter                      │
│  ├─ /ws/notifications/          │
│  └─ /ws/events/<org_id>/        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Consumer                       │
│  ├─ NotificationConsumer        │
│  └─ OrganizationEventsConsumer  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Redis Channel Layer            │
│  (Message broadcasting)         │
└─────────────────────────────────┘
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `channels[daphne]==4.0.0` - Django Channels with Daphne ASGI server
- `channels-redis==4.2.0` - Redis channel layer backend

### 2. Run Migrations

No new migrations required. WebSocket functionality uses existing models:
- `User` - For authentication
- `Org` - For organization events
- `Membership` - For membership verification

### 3. Start Redis

Ensure Redis is running (used for channel layer):

```bash
# Docker
docker run -p 6379:6379 redis:latest

# Or use existing Redis from docker-compose
docker-compose up redis
```

### 4. Run the Server

```bash
# Using Daphne (recommended for production)
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or Django development server (supports both HTTP and WebSockets)
python manage.py runserver
```

## Testing

### Run All WebSocket Tests

```bash
pytest src/api/tests/test_websockets.py -v
```

### Test Coverage

The test suite covers:
- ✓ Authentication with valid JWT tokens
- ✓ Authentication with invalid tokens
- ✓ Authentication via query string and headers
- ✓ Unauthorized access rejection
- ✓ Organization membership verification
- ✓ Connection establishment and welcome messages
- ✓ Notification broadcasting to specific users
- ✓ Organization event broadcasting to members
- ✓ Ping/pong keep-alive mechanism
- ✓ Invalid JSON handling
- ✓ Message isolation between users
- ✓ Message isolation between organizations
- ✓ Multiple users receiving same org event
- ✓ Graceful disconnection

### Test Results

All tests use:
- `pytest` with async support (`pytest-asyncio`)
- `channels.testing.WebsocketCommunicator` for WebSocket testing
- In-memory channel layer (no Redis required for tests)
- Mocked JWT validation (no Keycloak required for tests)

## Usage Examples

### Frontend (JavaScript)

```javascript
// Connect to notifications
const ws = new WebSocket(
  `ws://localhost:8000/ws/notifications/?token=${jwtToken}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'notification') {
    showNotification(data.notification);
  }
};
```

### Backend (Django)

```python
# From a view or Celery task
from asgiref.sync import async_to_sync
from api.consumers import broadcast_notification

async_to_sync(broadcast_notification)("user-123", {
    "title": "Task Complete",
    "body": "Your export is ready"
})
```

### Integration with Signals

```python
# In api/signals.py
from django.db.models.signals import post_save
from asgiref.sync import async_to_sync
from api.consumers import broadcast_org_event

@receiver(post_save, sender=SampleResource)
def resource_created(sender, instance, created, **kwargs):
    if created:
        async_to_sync(broadcast_org_event)(
            org_id=str(instance.org_id),
            event_type="resource.created",
            data={"resource_id": str(instance.id)}
        )
```

## Configuration

### Development

Default configuration in `base.py`:

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}
```

### Testing

In `test.py`:

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

### Production

Same as development, but ensure Redis is properly configured:

```bash
export REDIS_HOST=redis.production.example.com
export REDIS_PORT=6379
```

## Error Handling

### Connection Errors

- `4001` - Unauthorized (no valid JWT token)
- `4003` - Forbidden (not a member of organization)

### Client-Side Reconnection

Implement exponential backoff:

```javascript
let retries = 0;

function connect() {
  const ws = new WebSocket(url);

  ws.onclose = () => {
    const delay = Math.min(1000 * Math.pow(2, retries), 30000);
    setTimeout(connect, delay);
    retries++;
  };

  ws.onopen = () => {
    retries = 0; // Reset on successful connection
  };
}
```

## Performance Considerations

1. **Channel Layer:** Redis is required for production
2. **Connection Limits:** Monitor concurrent WebSocket connections
3. **Message Size:** Keep messages small for better performance
4. **Broadcasting:** Use group messaging (efficient) vs individual sends
5. **Scaling:** Use Redis Cluster for horizontal scaling

## Security Best Practices

1. **Always validate JWT tokens** on connection
2. **Verify organization membership** for org events
3. **Use AllowedHostsOriginValidator** to prevent CSRF
4. **Implement rate limiting** on message sending (TODO)
5. **Monitor for abuse** (connection flooding, message spam)
6. **Use WSS (WebSocket Secure)** in production

## Future Enhancements

Potential additions:

1. **Rate Limiting** - Limit messages per user/connection
2. **Presence Tracking** - Track online/offline status
3. **Message History** - Store recent messages in Redis
4. **Typing Indicators** - For chat-like features
5. **Read Receipts** - Track message delivery/read status
6. **Custom Permissions** - Integration with Cerbos for fine-grained access
7. **Metrics** - Track connection counts, message rates, errors

## Troubleshooting

### Connection Rejected (4001)

- Check JWT token is valid and not expired
- Verify token is passed correctly (query string or header)
- Check Keycloak is accessible and JWKS URL is correct

### Connection Rejected (4003)

- Verify user has membership in the organization
- Check organization ID is correct (UUID format)
- Ensure organization exists in database

### Messages Not Received

- Verify Redis is running and accessible
- Check channel layer configuration
- Ensure user is connected to correct endpoint
- Check user_id matches the JWT sub claim

### Tests Failing

- Ensure pytest-asyncio is installed
- Check `InMemoryChannelLayer` is configured in test.py
- Verify mocks are properly patching authentication

## Resources

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Daphne ASGI Server](https://github.com/django/daphne)
- [channels-redis](https://github.com/django/channels_redis)
- [WebSocket Protocol (RFC 6455)](https://tools.ietf.org/html/rfc6455)

## Support

For issues or questions:
1. Check WEBSOCKET_USAGE.md for usage examples
2. Review test cases in test_websockets.py
3. Check Django Channels documentation
4. Verify Redis configuration and connectivity

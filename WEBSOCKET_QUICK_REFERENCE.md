# WebSocket Quick Reference

Quick reference for common WebSocket operations in the Django boilerplate.

## Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `ws://localhost:8000/ws/notifications/` | JWT required | User-specific notifications |
| `ws://localhost:8000/ws/events/<org_id>/` | JWT + Org member | Organization-wide events |

## Client Connection

### JavaScript/Browser

```javascript
// Notifications
const ws = new WebSocket('ws://localhost:8000/ws/notifications/?token=' + jwtToken);

// Organization Events
const orgId = '123e4567-e89b-12d3-a456-426614174000';
const ws = new WebSocket(`ws://localhost:8000/ws/events/${orgId}/?token=${jwtToken}`);

// Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

// Keep-alive ping
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));
}, 30000);
```

### Python Client

```python
import asyncio
import websockets
import json

async def connect_notifications(token):
    uri = f"ws://localhost:8000/ws/notifications/?token={token}"
    async with websockets.connect(uri) as websocket:
        # Receive welcome message
        message = await websocket.recv()
        print(json.loads(message))

        # Listen for notifications
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(connect_notifications("your-jwt-token"))
```

## Backend Broadcasting

### From Async Context (Views/Consumers)

```python
from api.consumers import broadcast_notification, broadcast_org_event

# Send notification
await broadcast_notification("user-123", {
    "title": "Hello",
    "body": "You have a new message",
    "timestamp": "2025-01-15T10:30:00Z"
})

# Send org event
await broadcast_org_event("org-456", "resource.created", {
    "resource_id": "res-789",
    "resource_type": "document"
})
```

### From Sync Context (Celery Tasks/Signals)

```python
from asgiref.sync import async_to_sync
from api.consumers import broadcast_notification, broadcast_org_event

# Send notification
async_to_sync(broadcast_notification)("user-123", {
    "title": "Task Complete",
    "body": "Your export is ready"
})

# Send org event
async_to_sync(broadcast_org_event)("org-456", "task.completed", {
    "task_id": "task-789"
})
```

## Message Formats

### Connection Established

```json
{
  "type": "connection.established",
  "message": "Connected to notifications",
  "user_id": "test-user-123"
}
```

### Notification

```json
{
  "type": "notification",
  "notification": {
    "title": "Task Complete",
    "body": "Your export is ready",
    "timestamp": "2025-01-15T10:30:00Z",
    "action_url": "/downloads/export.csv"
  }
}
```

### Organization Event

```json
{
  "type": "event",
  "event_type": "resource.created",
  "data": {
    "resource_id": "res-123",
    "resource_name": "My Document",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

### Ping/Pong

```javascript
// Send
{ "type": "ping", "timestamp": "2025-01-15T10:30:00Z" }

// Receive
{ "type": "pong", "timestamp": "2025-01-15T10:30:00Z" }
```

### Error

```json
{
  "type": "error",
  "message": "Invalid JSON"
}
```

## Common Patterns

### Django Signals Integration

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from api.consumers import broadcast_org_event
from api.models import SampleResource

@receiver(post_save, sender=SampleResource)
def resource_saved(sender, instance, created, **kwargs):
    if created:
        async_to_sync(broadcast_org_event)(
            org_id=str(instance.org_id),
            event_type="resource.created",
            data={"resource_id": str(instance.id)}
        )
```

### Celery Task Broadcasting

```python
from celery import shared_task
from asgiref.sync import async_to_sync
from api.consumers import broadcast_notification

@shared_task
def export_data(user_id, file_path):
    # ... export logic ...

    async_to_sync(broadcast_notification)(user_id, {
        "title": "Export Complete",
        "body": "Your data export is ready",
        "action_url": file_path
    })
```

### React Hook

```javascript
import { useEffect, useRef, useState } from 'react';

function useWebSocket(url, token) {
  const [messages, setMessages] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket(`${url}?token=${token}`);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, data]);
    };

    return () => ws.current?.close();
  }, [url, token]);

  return messages;
}

// Usage
function NotificationPanel({ token }) {
  const messages = useWebSocket('ws://localhost:8000/ws/notifications/', token);

  return (
    <div>
      {messages.map((msg, i) => (
        <div key={i}>{msg.notification?.title}</div>
      ))}
    </div>
  );
}
```

## Testing

### Run Tests

```bash
# All WebSocket tests
pytest src/api/tests/test_websockets.py -v

# Specific test
pytest src/api/tests/test_websockets.py::test_notification_consumer_connect_authenticated -v

# With coverage
pytest src/api/tests/test_websockets.py --cov=api.consumers --cov=api.middleware
```

### Mock Authentication in Tests

```python
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_jwt_auth():
    def _mock_validate(token: str):
        return {
            "sub": "test-user-123",
            "email": "test@example.com"
        }
    return _mock_validate

@pytest.mark.asyncio
async def test_example(mock_jwt_auth):
    with patch("api.middleware.KeycloakJWTAuthentication._validate_token", side_effect=mock_jwt_auth):
        # Your test code
        pass
```

## Error Codes

| Code | Meaning | Cause |
|------|---------|-------|
| 4001 | Unauthorized | Missing or invalid JWT token |
| 4003 | Forbidden | Not a member of the organization |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_HOST` | `redis` | Redis hostname for channel layer |
| `REDIS_PORT` | `6379` | Redis port |
| `KEYCLOAK_JWKS_URL` | Auto-generated | JWT validation endpoint |

## Deployment

### Development

```bash
# Start Redis
docker run -p 6379:6379 redis:latest

# Start Django with Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Production

```bash
# systemd service
sudo systemctl start django-websocket

# Or with gunicorn + uvicorn workers
gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Nginx Reverse Proxy

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## Debugging

### Check Redis Connection

```bash
redis-cli ping
# Should return: PONG
```

### Test Channel Layer

```python
python manage.py shell

from channels.layers import get_channel_layer
channel_layer = get_channel_layer()

# Send test message
import asyncio
asyncio.run(channel_layer.group_send("test_group", {
    "type": "test.message",
    "text": "Hello"
}))
```

### View Connected Clients

```python
# In Django shell
from channels.layers import get_channel_layer
import asyncio

channel_layer = get_channel_layer()
# Note: This requires custom implementation for tracking
```

## Performance Tips

1. **Keep messages small** - Minimize JSON payload size
2. **Use groups** - More efficient than individual sends
3. **Implement reconnection** - Handle disconnects gracefully
4. **Rate limit** - Prevent spam/abuse
5. **Monitor Redis** - Watch memory usage and connection count

## Security Checklist

- ✓ JWT tokens validated on every connection
- ✓ Organization membership verified for org events
- ✓ AllowedHostsOriginValidator prevents CSRF
- ✓ WSS (WebSocket Secure) used in production
- ✓ Tokens not logged or exposed
- ✓ Rate limiting implemented (TODO)
- ✓ Input validation on all messages

## Common Event Types

### User Notifications
- `task.completed`
- `task.failed`
- `message.received`
- `mention.received`
- `system.alert`

### Organization Events
- `resource.created`
- `resource.updated`
- `resource.deleted`
- `member.joined`
- `member.left`
- `system.alert`
- `quota.warning`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection rejected | Check JWT token validity and expiration |
| 4003 Forbidden | Verify user has org membership |
| Messages not received | Check Redis is running and configured |
| Tests failing | Ensure InMemoryChannelLayer in test.py |
| Import errors | Install channels: `pip install channels[daphne]` |

## Resources

- Full documentation: `WEBSOCKET_USAGE.md`
- Implementation details: `WEBSOCKET_IMPLEMENTATION.md`
- Test examples: `src/api/tests/test_websockets.py`
- Signal integration: `src/api/websocket_signals.py`

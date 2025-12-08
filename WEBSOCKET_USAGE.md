# WebSocket Usage Guide

This guide explains how to use the WebSocket functionality implemented with Django Channels in the Django boilerplate.

## Overview

The boilerplate includes two WebSocket consumers:

1. **NotificationConsumer** - For user-specific notifications
2. **OrganizationEventsConsumer** - For organization-wide events

Both consumers use JWT authentication via Keycloak, following the same authentication pattern as the REST API.

## Installation

Dependencies have been added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running the Server

Use Daphne (included with Django Channels) to run the ASGI server:

```bash
# Development
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or use Django's development server (supports both ASGI and WSGI)
python manage.py runserver
```

## WebSocket Endpoints

### 1. User Notifications

**Endpoint:** `ws://localhost:8000/ws/notifications/`

**Authentication:** JWT token required (via query string or headers)

**Connection Examples:**

```javascript
// Using query string
const ws = new WebSocket('ws://localhost:8000/ws/notifications/?token=YOUR_JWT_TOKEN');

// Using headers (if your client supports it)
const ws = new WebSocket('ws://localhost:8000/ws/notifications/');
// Set Authorization header: Bearer YOUR_JWT_TOKEN
```

**Received Messages:**

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'connection.established') {
    console.log('Connected:', data.message);
    console.log('User ID:', data.user_id);
  }

  if (data.type === 'notification') {
    console.log('Notification:', data.notification);
    // data.notification contains: { title, body, timestamp, ... }
  }
};
```

**Ping/Pong (Keep-Alive):**

```javascript
// Send ping
ws.send(JSON.stringify({
  type: 'ping',
  timestamp: new Date().toISOString()
}));

// Receive pong
// { type: 'pong', timestamp: '...' }
```

### 2. Organization Events

**Endpoint:** `ws://localhost:8000/ws/events/<org_id>/`

**Authentication:** JWT token required + user must be a member of the organization

**Connection Example:**

```javascript
const orgId = '123e4567-e89b-12d3-a456-426614174000';
const ws = new WebSocket(`ws://localhost:8000/ws/events/${orgId}/?token=YOUR_JWT_TOKEN`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'connection.established') {
    console.log('Connected to org:', data.org_id);
  }

  if (data.type === 'event') {
    console.log('Event type:', data.event_type);
    console.log('Event data:', data.data);
    // Example: event_type = "user.joined", data = { user_id, user_email, timestamp }
  }
};
```

## Broadcasting Messages from Backend

### Broadcasting Notifications

From anywhere in your Django code (views, tasks, signals):

```python
from api.consumers import broadcast_notification

# In async context
await broadcast_notification("user-123", {
    "title": "New Message",
    "body": "You have a new message from John",
    "timestamp": "2025-01-15T10:30:00Z",
    "link": "/messages/456"
})

# In sync context (e.g., Celery task)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

async_to_sync(broadcast_notification)("user-123", {
    "title": "Task Completed",
    "body": "Your export is ready for download"
})
```

### Broadcasting Organization Events

```python
from api.consumers import broadcast_org_event

# In async context
await broadcast_org_event(
    org_id="org-123",
    event_type="user.joined",
    data={
        "user_id": "user-456",
        "user_email": "newuser@example.com",
        "timestamp": "2025-01-15T10:30:00Z"
    }
)

# In sync context
from asgiref.sync import async_to_sync

async_to_sync(broadcast_org_event)(
    org_id="org-123",
    event_type="resource.created",
    data={
        "resource_id": "res-789",
        "resource_type": "document",
        "created_by": "user-123"
    }
)
```

## Example: Celery Task Broadcasting

```python
# In api/tasks.py
from celery import shared_task
from asgiref.sync import async_to_sync
from api.consumers import broadcast_notification, broadcast_org_event

@shared_task
def process_document(user_id, org_id, document_id):
    # ... process document ...

    # Notify the user
    async_to_sync(broadcast_notification)(user_id, {
        "title": "Document Processed",
        "body": f"Document {document_id} has been processed successfully",
        "timestamp": timezone.now().isoformat()
    })

    # Notify the organization
    async_to_sync(broadcast_org_event)(org_id, "document.processed", {
        "document_id": document_id,
        "processed_by": user_id,
        "timestamp": timezone.now().isoformat()
    })
```

## Example: Django Signal Broadcasting

```python
# In api/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from api.consumers import broadcast_org_event
from api.models import SampleResource

@receiver(post_save, sender=SampleResource)
def resource_created_handler(sender, instance, created, **kwargs):
    if created:
        async_to_sync(broadcast_org_event)(
            org_id=str(instance.org_id),
            event_type="resource.created",
            data={
                "resource_id": str(instance.id),
                "resource_name": instance.name,
                "created_at": instance.created_at.isoformat()
            }
        )
```

## Error Codes

WebSocket connections may be closed with the following custom codes:

- `4001` - Unauthorized (no valid JWT token)
- `4003` - Forbidden (not a member of the organization)

## Testing

Run the WebSocket tests:

```bash
pytest backend/api/tests/test_websockets.py -v
```

The test suite includes:
- Authentication tests (valid/invalid tokens)
- Connection tests for both consumers
- Message broadcasting tests
- Ping/pong keep-alive tests
- Multi-user isolation tests
- Organization membership verification tests

## Architecture

```
Client (WebSocket)
    ↓
ASGI Server (Daphne)
    ↓
ProtocolTypeRouter
    ↓
AllowedHostsOriginValidator
    ↓
JWTAuthMiddleware (validates Keycloak JWT)
    ↓
URLRouter (routes to appropriate consumer)
    ↓
Consumer (NotificationConsumer or OrganizationEventsConsumer)
    ↓
Redis Channel Layer (for message broadcasting)
```

## Configuration

All configuration is in `config/settings/base.py`:

```python
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST", "redis"), int(os.getenv("REDIS_PORT", "6379")))],
        },
    },
}
```

## Security Considerations

1. **Authentication**: All WebSocket connections require valid JWT tokens from Keycloak
2. **Authorization**: Organization events require membership verification
3. **Origin Validation**: `AllowedHostsOriginValidator` prevents unauthorized origins
4. **Message Isolation**: Users only receive messages in their groups
5. **Channel Groups**: Each user/org has isolated channel groups

## Frontend Example (React)

```javascript
import { useEffect, useRef, useState } from 'react';

function useNotifications(token) {
  const [notifications, setNotifications] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    if (!token) return;

    // Connect to WebSocket
    ws.current = new WebSocket(
      `ws://localhost:8000/ws/notifications/?token=${token}`
    );

    ws.current.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'notification') {
        setNotifications(prev => [...prev, data.notification]);
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
    };

    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token]);

  return notifications;
}

// Usage
function NotificationPanel() {
  const token = localStorage.getItem('jwt_token');
  const notifications = useNotifications(token);

  return (
    <div>
      <h2>Notifications</h2>
      {notifications.map((notif, idx) => (
        <div key={idx}>
          <h3>{notif.title}</h3>
          <p>{notif.body}</p>
        </div>
      ))}
    </div>
  );
}
```

## Production Deployment

For production, use Daphne with a process manager like systemd or supervisord:

```ini
# /etc/systemd/system/django-websocket.service
[Unit]
Description=Django WebSocket Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Or use Nginx as a reverse proxy:

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

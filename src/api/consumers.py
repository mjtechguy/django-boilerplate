"""WebSocket consumers for Django Channels."""
import json
from typing import Any, Dict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from api.models import Membership, Org


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user-specific notifications.

    Authenticated users join a channel group based on their user ID.
    Messages can be broadcast to specific users via broadcast_notification().

    URL: ws/notifications/
    Auth: JWT token required (via query string or headers)
    """

    async def connect(self):
        """Accept connection if user is authenticated."""
        user = self.scope.get("user")

        if not user or isinstance(user, AnonymousUser):
            await self.close(code=4001)  # Custom close code for unauthorized
            return

        # Each user has their own notification channel
        self.user_id = str(user.username)
        self.group_name = f"notifications_{self.user_id}"

        # Join user's notification group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        # Send welcome message
        await self.send(text_data=json.dumps({
            "type": "connection.established",
            "message": "Connected to notifications",
            "user_id": self.user_id,
        }))

    async def disconnect(self, close_code):
        """Leave notification group on disconnect."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages from WebSocket.

        Clients can send ping messages to keep connection alive.
        """
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get("type")

                if message_type == "ping":
                    await self.send(text_data=json.dumps({
                        "type": "pong",
                        "timestamp": data.get("timestamp"),
                    }))
            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid JSON",
                }))

    async def notification_message(self, event):
        """
        Handler for notification.message events sent to the group.

        This is called when broadcast_notification() sends a message.
        """
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event["notification"],
        }))


class OrganizationEventsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for organization-wide events.

    Authenticated users join a channel group for their organization.
    Only organization members can connect.
    Events are broadcast to all members of the organization.

    URL: ws/events/<org_id>/
    Auth: JWT token required + org membership verification
    """

    async def connect(self):
        """Accept connection if user is authenticated and is org member."""
        user = self.scope.get("user")
        self.org_id = self.scope["url_route"]["kwargs"]["org_id"]

        if not user or isinstance(user, AnonymousUser):
            await self.close(code=4001)  # Unauthorized
            return

        # Verify user is a member of the organization
        is_member = await self._check_org_membership(user, self.org_id)
        if not is_member:
            await self.close(code=4003)  # Forbidden
            return

        # Join organization events group
        self.group_name = f"org_events_{self.org_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        # Send welcome message
        await self.send(text_data=json.dumps({
            "type": "connection.established",
            "message": f"Connected to organization events",
            "org_id": self.org_id,
        }))

    async def disconnect(self, close_code):
        """Leave organization group on disconnect."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages from WebSocket.

        Clients can send ping messages to keep connection alive.
        """
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get("type")

                if message_type == "ping":
                    await self.send(text_data=json.dumps({
                        "type": "pong",
                        "timestamp": data.get("timestamp"),
                    }))
            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid JSON",
                }))

    async def org_event(self, event):
        """
        Handler for org.event messages sent to the group.

        This is called when broadcast_org_event() sends a message.
        """
        await self.send(text_data=json.dumps({
            "type": "event",
            "event_type": event["event_type"],
            "data": event["data"],
        }))

    @database_sync_to_async
    def _check_org_membership(self, user, org_id: str) -> bool:
        """Check if user is a member of the organization."""
        try:
            # Verify org exists
            Org.objects.get(id=org_id)

            # Check if user has membership in this org
            return Membership.objects.filter(
                user=user,
                org_id=org_id
            ).exists()
        except (Org.DoesNotExist, ValueError):
            return False


# Helper functions for broadcasting messages


async def broadcast_notification(user_id: str, notification: Dict[str, Any]):
    """
    Broadcast a notification to a specific user.

    Args:
        user_id: The user's ID (username/sub from JWT)
        notification: Dictionary containing notification data

    Example:
        await broadcast_notification("user-123", {
            "title": "New message",
            "body": "You have a new message from John",
            "timestamp": "2025-01-15T10:30:00Z"
        })
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    group_name = f"notifications_{user_id}"

    await channel_layer.group_send(
        group_name,
        {
            "type": "notification.message",
            "notification": notification,
        }
    )


async def broadcast_org_event(org_id: str, event_type: str, data: Dict[str, Any]):
    """
    Broadcast an event to all members of an organization.

    Args:
        org_id: The organization ID
        event_type: Type of event (e.g., "user.joined", "resource.created")
        data: Event-specific data

    Example:
        await broadcast_org_event("org-123", "user.joined", {
            "user_id": "user-456",
            "user_email": "newuser@example.com",
            "timestamp": "2025-01-15T10:30:00Z"
        })
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    group_name = f"org_events_{org_id}"

    await channel_layer.group_send(
        group_name,
        {
            "type": "org.event",
            "event_type": event_type,
            "data": data,
        }
    )

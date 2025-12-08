"""WebSocket URL routing for Django Channels."""
from django.urls import re_path

from api import consumers

websocket_urlpatterns = [
    # User-specific notifications
    # ws://localhost:8000/ws/notifications/?token=<jwt>
    re_path(r"ws/notifications/$", consumers.NotificationConsumer.as_asgi()),

    # Organization-wide events
    # ws://localhost:8000/ws/events/<org_id>/?token=<jwt>
    re_path(r"ws/events/(?P<org_id>[^/]+)/$", consumers.OrganizationEventsConsumer.as_asgi()),
]

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# Initialize Django ASGI application early to ensure apps are loaded
# before importing routing and middleware
django_asgi_app = get_asgi_application()

# Import after Django initialization to avoid AppRegistryNotReady
from api.middleware import JWTAuthMiddleware
from api.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Django's ASGI application handles HTTP requests
    "http": django_asgi_app,

    # WebSocket handler with JWT authentication and allowed hosts validation
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})

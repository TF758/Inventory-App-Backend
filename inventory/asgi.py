import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import db_inventory.routing
from inventory.middleware import JWTAuthMiddleware
from db_inventory.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
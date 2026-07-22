import os

from settings_selector import resolve_settings_module

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    resolve_settings_module(default_environment="dev"),
)

import django

django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from core.routing import websocket_urlpatterns
from inventory.middleware import JWTAuthMiddleware


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
            )
        ),
    }
)

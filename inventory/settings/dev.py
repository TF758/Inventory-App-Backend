from . import *


DEBUG = True


EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


INSTALLED_APPS += [
    "django_extensions",
]


# Local development does not need distributed
# cross-process WebSocket messaging.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": (
            "channels.layers.InMemoryChannelLayer"
        ),
    },
}


SITES_OPTION_CACHE_DEBUG_HEADERS = True


SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_SSL_REDIRECT = False
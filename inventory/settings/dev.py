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

# Explicit development-only conveniences. Production and staging settings
# force these values off regardless of environment configuration.
ENABLE_BASIC_AUTH = env.bool(
    "ENABLE_BASIC_AUTH",
    default=True,
)

basic_authentication_class = (
    "rest_framework.authentication.BasicAuthentication"
)

if ENABLE_BASIC_AUTH:
    if basic_authentication_class not in REST_FRAMEWORK[
        "DEFAULT_AUTHENTICATION_CLASSES"
    ]:
        REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].append(
            basic_authentication_class
        )
else:
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
        authentication_class
        for authentication_class in REST_FRAMEWORK[
            "DEFAULT_AUTHENTICATION_CLASSES"
        ]
        if authentication_class != basic_authentication_class
    ]

WEBSOCKET_ALLOW_QUERY_TOKEN = env.bool(
    "WEBSOCKET_ALLOW_QUERY_TOKEN",
    default=True,
)
API_DOCS_ENABLED = env.bool(
    "API_DOCS_ENABLED",
    default=True,
)
API_DOCS_PUBLIC = env.bool(
    "API_DOCS_PUBLIC",
    default=True,
)
METRICS_ALLOW_PUBLIC = env.bool(
    "METRICS_ALLOW_PUBLIC",
    default=True,
)

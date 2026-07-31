from . import *


DEBUG = False

# Production and staging must never expose development authentication
# shortcuts, query-string WebSocket credentials, or public operational
# endpoints even when an environment variable is misconfigured.
ENABLE_BASIC_AUTH = False
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    authentication_class
    for authentication_class in REST_FRAMEWORK[
        "DEFAULT_AUTHENTICATION_CLASSES"
    ]
    if authentication_class
    != "rest_framework.authentication.BasicAuthentication"
]

WEBSOCKET_ALLOW_QUERY_TOKEN = False
API_DOCS_PUBLIC = False
METRICS_ALLOW_PUBLIC = False

API_DOCS_ENABLED = env.bool(
    "API_DOCS_ENABLED",
    default=False,
)

SECURE_CONTENT_TYPE_NOSNIFF = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = env.int(
    "SECURE_HSTS_SECONDS",
    default=31536000,
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)

SECURE_HSTS_PRELOAD = env.bool(
    "SECURE_HSTS_PRELOAD",
    default=False,
)

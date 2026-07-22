# inventory/settings/security.py

from .base import APP_ENV, DEBUG, IS_TESTING, env

# -------------------------------------------------
# Cookie / Security Settings
# -------------------------------------------------

default_secure = not (DEBUG or IS_TESTING)

SESSION_COOKIE_SECURE = env.bool(
    "SESSION_COOKIE_SECURE",
    default=default_secure,
)

CSRF_COOKIE_SECURE = env.bool(
    "CSRF_COOKIE_SECURE",
    default=default_secure,
)

SESSION_COOKIE_SAMESITE = env(
    "SESSION_COOKIE_SAMESITE",
    default="None" if default_secure else "Lax",
)

CSRF_COOKIE_SAMESITE = env(
    "CSRF_COOKIE_SAMESITE",
    default="None" if default_secure else "Lax",
)

SECURE_SSL_REDIRECT = env.bool(
    "SECURE_SSL_REDIRECT",
    default=default_secure,
)

# -------------------------------------------------
# Operational endpoint boundaries
# -------------------------------------------------

WEBSOCKET_ALLOW_QUERY_TOKEN = env.bool(
    "WEBSOCKET_ALLOW_QUERY_TOKEN",
    default=APP_ENV in {"dev", "local"},
)

API_DOCS_ENABLED = env.bool(
    "API_DOCS_ENABLED",
    default=APP_ENV in {"dev", "local", "staging"},
)

API_DOCS_PUBLIC = env.bool(
    "API_DOCS_PUBLIC",
    default=APP_ENV in {"dev", "local"},
)

METRICS_ALLOW_PUBLIC = env.bool(
    "METRICS_ALLOW_PUBLIC",
    default=APP_ENV in {"dev", "local"},
)

METRICS_BEARER_TOKEN = env(
    "METRICS_BEARER_TOKEN",
    default="",
)

# -------------------------------------------------
# Additional Security Headers
# -------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"

# -------------------------------------------------
# Session Security
# -------------------------------------------------

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = True

# -------------------------------------------------
# Reverse Proxy Support
# -------------------------------------------------

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

USE_X_FORWARDED_HOST = True

# -------------------------------------------------
# CSRF
# -------------------------------------------------

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://localhost:8000",
    ],
)

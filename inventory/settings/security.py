# inventory/settings/security.py

from .base import env, DEBUG, IS_TESTING

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
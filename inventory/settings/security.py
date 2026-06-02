# inventory/settings/security.py

from .base import env, DEBUG, IS_TESTING

# -------------------------------------------------
# Cookie / Security Settings
# -------------------------------------------------

if DEBUG or IS_TESTING:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

    SECURE_SSL_REDIRECT = False

else:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"

    SECURE_SSL_REDIRECT = True

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
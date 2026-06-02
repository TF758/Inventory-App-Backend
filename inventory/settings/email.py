
from inventory.settings import IS_TESTING

from .base import env, DEBUG

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = env(
    "EMAIL_HOST",
    default="smtp.gmail.com",
)

EMAIL_PORT = env.int(
    "EMAIL_PORT",
    default=587,
)

EMAIL_USE_TLS = env.bool(
    "EMAIL_USE_TLS",
    default=True,
)

EMAIL_HOST_USER = env(
    "EMAIL_HOST_USER",
    default="",
)

EMAIL_HOST_PASSWORD = env(
    "EMAIL_HOST_PASSWORD",
    default="",
)

DEFAULT_FROM_EMAIL = (
    EMAIL_HOST_USER
    or "no-reply@localhost"
)

# Production safety check
if not DEBUG and not IS_TESTING:
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise ValueError(
            "EMAIL_HOST_USER and EMAIL_HOST_PASSWORD "
            "must be set in production"
        )
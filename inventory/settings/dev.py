from . import *

DEBUG = True

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_SSL_REDIRECT = False
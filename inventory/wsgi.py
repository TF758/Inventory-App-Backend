"""WSGI config for the inventory project."""

import os

from django.core.wsgi import get_wsgi_application

from settings_selector import resolve_settings_module


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    resolve_settings_module(default_environment="dev"),
)

application = get_wsgi_application()

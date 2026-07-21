import os

from celery import Celery

from settings_selector import resolve_settings_module


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    resolve_settings_module(default_environment="dev"),
)

app = Celery("inventory")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

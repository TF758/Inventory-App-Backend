"""Resolve the Django settings module from explicit environment configuration."""

from __future__ import annotations

import os


_SETTINGS_BY_ENVIRONMENT = {
    "local": "inventory.settings.dev",
    "dev": "inventory.settings.dev",
    "development": "inventory.settings.dev",
    "test": "inventory.settings.test",
    "ci": "inventory.settings.ci",
    "staging": "inventory.settings.staging",
    "prod": "inventory.settings.prod",
    "production": "inventory.settings.prod",
}


def resolve_settings_module(*, default_environment: str = "dev") -> str:
    """Return an explicit Django settings module for the current process.

    ``DJANGO_SETTINGS_MODULE`` always wins. Otherwise ``APP_ENV`` and then
    ``DJANGO_ENV`` are mapped to one of the project's concrete settings files.
    Local commands default to the development settings module.
    """

    explicit_module = os.getenv("DJANGO_SETTINGS_MODULE")
    if explicit_module:
        return explicit_module

    environment = (
        os.getenv("APP_ENV")
        or os.getenv("DJANGO_ENV")
        or default_environment
    ).strip().lower()

    try:
        return _SETTINGS_BY_ENVIRONMENT[environment]
    except KeyError as exc:
        supported = ", ".join(sorted(_SETTINGS_BY_ENVIRONMENT))
        raise RuntimeError(
            f"Unsupported application environment '{environment}'. "
            f"Expected one of: {supported}."
        ) from exc

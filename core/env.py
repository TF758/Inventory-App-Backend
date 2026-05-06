
import os

from django.core.exceptions import ImproperlyConfigured


REQUIRED_ENV_VARS = [
    "SECRET_KEY",

    # Database
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
]


def get_env_variable(name: str) -> str:
    """
    Return environment variable or raise a clear exception.
    """

    value = os.getenv(name)

    if value is None or value.strip() == "":
        raise ImproperlyConfigured(
            f"Missing required environment variable: {name}"
        )

    return value


def validate_required_env_vars() -> None:
    """
    Validate all required environment variables at startup.
    """

    missing = []

    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)

        if value is None or value.strip() == "":
            missing.append(var)

    if missing:
        raise ImproperlyConfigured(
            "Missing required environment variables: "
            + ", ".join(sorted(missing))
        )


def env_str(name: str, default=None) -> str:
    """
    Read string environment variable.
    """

    value = os.getenv(name, default)

    if value is None:
        raise ImproperlyConfigured(
            f"Missing environment variable: {name}"
        )

    return value


def env_int(name: str, default=None) -> int:
    """
    Read integer environment variable.
    """

    value = env_str(name, default)

    try:
        return int(value)

    except (TypeError, ValueError):
        raise ImproperlyConfigured(
            f"Environment variable '{name}' must be an integer"
        )


def env_bool(name: str, default=False) -> bool:
    """
    Read boolean environment variable.
    """

    value = str(os.getenv(name, default)).lower()

    return value in ("1", "true", "yes", "on")
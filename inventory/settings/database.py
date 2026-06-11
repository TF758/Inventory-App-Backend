from .base import env

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="db"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": env.int(
            "DB_CONN_MAX_AGE",
            default=60,
        ),
    }
}
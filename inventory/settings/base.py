from pathlib import Path
from datetime import timedelta
import environ
import os
import sys

IS_TESTING = "test" in sys.argv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

IN_DOCKER = os.path.exists("/.dockerenv")

DJANGO_ENV = os.environ.get(
    "DJANGO_ENV",
    "dev" if IN_DOCKER else "local",
)

env = environ.Env(DEBUG=(bool, False))

env_file = BASE_DIR / f".env.{DJANGO_ENV}"

if env_file.exists():
    environ.Env.read_env(env_file)
else:
    print(f"Warning: env file not found: {env_file}")

SECRET_KEY = env("SECRET_KEY")

from core.env import validate_required_env_vars

validate_required_env_vars()

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"]
)

FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "http://localhost:5173"
)

ROOT_URLCONF = "inventory.urls"

WSGI_APPLICATION = "inventory.wsgi.application"

ASGI_APPLICATION = "inventory.asgi.application"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

     "django_prometheus",

    "core",

    "assets",
    "authorization",
    "assignments",
    "agreements",
    "sites",
    "users",
    "reporting",
    "analytics",
    "data_import",

    "drf_spectacular",

    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_extensions",

    "django_celery_results",
    "django_celery_beat",

    "channels",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "core.middleware.RequestIDMiddleware",

    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware"
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

AUTH_USER_MODEL = "users.User"

LANGUAGE_CODE = "en-us"

TIME_ZONE = env("TIME_ZONE", default="UTC")

USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_ROOT.mkdir(exist_ok=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "x-csrftoken",
    "accept",
    "origin",
    "Content-Disposition",
    "x-device-name",
]

CORS_EXPOSE_HEADERS = [
    "Content-Disposition",
]

SNAPSHOT_SCHEMA_VERSION = env.int(
    "SNAPSHOT_SCHEMA_VERSION",
    default=1
)

# -------------------------------------------------
# Logging
# -------------------------------------------------

LOG_TO_CONSOLE = env.bool(
    "LOG_TO_CONSOLE",
    default=True,
)

# -------------------------------------------------
# Password validation
# -------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 3},
    },
]
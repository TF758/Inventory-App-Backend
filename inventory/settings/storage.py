from pathlib import Path

from .base import APP_ENV, BASE_DIR, MEDIA_URL, env


STORAGE_BACKEND = env(
    "STORAGE_BACKEND",
    default="filesystem",
).strip().lower()

# Filesystem storage is safe for local development and for a single-host
# deployment only when API and worker containers mount the same durable volume.
STORAGE_SHARED = env.bool(
    "STORAGE_SHARED",
    default=False,
)

MEDIA_ROOT = Path(
    env(
        "MEDIA_ROOT",
        default=str(BASE_DIR / "media"),
    )
)
REPORTS_DIR = Path(
    env(
        "REPORTS_DIR",
        default=str(BASE_DIR / "reports"),
    )
)

MEDIA_STORAGE_PREFIX = env(
    "MEDIA_STORAGE_PREFIX",
    default="media",
).strip("/")
REPORT_STORAGE_PREFIX = env(
    "REPORT_STORAGE_PREFIX",
    default="reports",
).strip("/")

AWS_STORAGE_BUCKET_NAME = env(
    "AWS_STORAGE_BUCKET_NAME",
    default="",
)
AWS_S3_REGION_NAME = env(
    "AWS_S3_REGION_NAME",
    default="",
)
AWS_S3_ENDPOINT_URL = env(
    "AWS_S3_ENDPOINT_URL",
    default="",
)
AWS_S3_ADDRESSING_STYLE = env(
    "AWS_S3_ADDRESSING_STYLE",
    default="",
)
AWS_S3_USE_SSL = env.bool(
    "AWS_S3_USE_SSL",
    default=True,
)
AWS_S3_VERIFY = env.bool(
    "AWS_S3_VERIFY",
    default=True,
)

_STATICFILES_STORAGE = {
    "BACKEND": (
        "whitenoise.storage."
        "CompressedManifestStaticFilesStorage"
    ),
}


def _s3_options(*, location: str, overwrite: bool) -> dict:
    options = {
        "bucket_name": AWS_STORAGE_BUCKET_NAME,
        "location": location,
        "default_acl": None,
        "file_overwrite": overwrite,
        "querystring_auth": True,
        "use_ssl": AWS_S3_USE_SSL,
        "verify": AWS_S3_VERIFY,
        "signature_version": "s3v4",
    }

    optional_values = {
        "region_name": AWS_S3_REGION_NAME,
        "endpoint_url": AWS_S3_ENDPOINT_URL,
        "addressing_style": AWS_S3_ADDRESSING_STYLE,
    }
    options.update(
        {
            key: value
            for key, value in optional_values.items()
            if value
        }
    )
    return options


if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": _s3_options(
                location=MEDIA_STORAGE_PREFIX,
                overwrite=False,
            ),
        },
        "reports": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": _s3_options(
                location=REPORT_STORAGE_PREFIX,
                overwrite=True,
            ),
        },
        "staticfiles": _STATICFILES_STORAGE,
    }
else:
    # Unknown backends intentionally fall back to filesystem so Django can
    # start and surface a clear deployment-system-check error.
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    STORAGES = {
        "default": {
            "BACKEND": (
                "django.core.files.storage.FileSystemStorage"
            ),
            "OPTIONS": {
                "location": MEDIA_ROOT,
                "base_url": MEDIA_URL,
            },
        },
        "reports": {
            "BACKEND": (
                "django.core.files.storage.FileSystemStorage"
            ),
            "OPTIONS": {
                "location": REPORTS_DIR,
            },
        },
        "staticfiles": _STATICFILES_STORAGE,
    }


# Exposed for project deployment checks and operational diagnostics.
STORAGE_IS_DISTRIBUTED = STORAGE_BACKEND == "s3"
STORAGE_IS_SHARED = STORAGE_IS_DISTRIBUTED or STORAGE_SHARED

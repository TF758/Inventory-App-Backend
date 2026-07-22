from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def production_boundary_checks(app_configs, **kwargs):
    """Validate project-specific production exposure boundaries."""

    del app_configs, kwargs

    environment = getattr(settings, "APP_ENV", "")
    if environment not in {"staging", "production"}:
        return []

    messages = []
    authentication_classes = settings.REST_FRAMEWORK.get(
        "DEFAULT_AUTHENTICATION_CLASSES",
        [],
    )

    if (
        "rest_framework.authentication.BasicAuthentication"
        in authentication_classes
    ):
        messages.append(
            Error(
                "Basic Authentication is enabled outside development.",
                id="inventory.E001",
            )
        )

    if settings.WEBSOCKET_ALLOW_QUERY_TOKEN:
        messages.append(
            Error(
                "WebSocket query-string JWT authentication is enabled.",
                id="inventory.E002",
            )
        )

    if settings.METRICS_ALLOW_PUBLIC:
        messages.append(
            Error(
                "Prometheus metrics are publicly accessible.",
                id="inventory.E003",
            )
        )

    if settings.API_DOCS_PUBLIC:
        messages.append(
            Error(
                "API documentation is publicly accessible.",
                id="inventory.E004",
            )
        )

    required_password_length = 12 if environment == "production" else 10
    if settings.PASSWORD_MIN_LENGTH < required_password_length:
        messages.append(
            Error(
                "PASSWORD_MIN_LENGTH is below the required environment "
                f"baseline of {required_password_length}.",
                id="inventory.E009",
            )
        )

    if not settings.METRICS_BEARER_TOKEN:
        messages.append(
            Warning(
                "METRICS_BEARER_TOKEN is empty; the metrics endpoint "
                "will remain unavailable.",
                id="inventory.W001",
            )
        )

    if environment == "production":
        if "*" in settings.ALLOWED_HOSTS:
            messages.append(
                Error(
                    "Production ALLOWED_HOSTS must not contain '*'.",
                    id="inventory.E005",
                )
            )

        secure_urls = {
            "FRONTEND_URL": getattr(settings, "FRONTEND_URL", ""),
        }
        for setting_name, value in secure_urls.items():
            if value and urlparse(value).scheme != "https":
                messages.append(
                    Error(
                        f"{setting_name} must use HTTPS in production.",
                        id="inventory.E006",
                    )
                )

        for origin in settings.CORS_ALLOWED_ORIGINS:
            if urlparse(origin).scheme != "https":
                messages.append(
                    Error(
                        "CORS_ALLOWED_ORIGINS must use HTTPS in production.",
                        id="inventory.E007",
                    )
                )
                break

        for origin in settings.CSRF_TRUSTED_ORIGINS:
            if urlparse(origin).scheme != "https":
                messages.append(
                    Error(
                        "CSRF_TRUSTED_ORIGINS must use HTTPS in production.",
                        id="inventory.E008",
                    )
                )
                break

    storage_aliases = getattr(settings, "STORAGES", {})
    missing_aliases = {"default", "reports"} - set(storage_aliases)
    if missing_aliases:
        messages.append(
            Error(
                "Required Django storage aliases are missing: "
                + ", ".join(sorted(missing_aliases)),
                id="inventory.E010",
            )
        )

    storage_backend = getattr(
        settings,
        "STORAGE_BACKEND",
        "filesystem",
    )

    if storage_backend not in {"filesystem", "s3"}:
        messages.append(
            Error(
                "STORAGE_BACKEND must be 'filesystem' or 's3'.",
                id="inventory.E011",
            )
        )
    elif storage_backend == "filesystem":
        if not getattr(settings, "STORAGE_SHARED", False):
            messages.append(
                Error(
                    "Filesystem storage is not declared shared across "
                    "API and worker services.",
                    id="inventory.E012",
                )
            )

        if environment == "production":
            messages.append(
                Warning(
                    "Production is using single-host shared filesystem "
                    "storage. Use the S3 backend before adding replicas "
                    "or multiple Docker hosts.",
                    id="inventory.W002",
                )
            )
    elif not getattr(settings, "AWS_STORAGE_BUCKET_NAME", ""):
        messages.append(
            Error(
                "AWS_STORAGE_BUCKET_NAME is required for S3 storage.",
                id="inventory.E013",
            )
        )

    if storage_backend == "s3" and environment == "production":
        endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", "")
        if endpoint_url and urlparse(endpoint_url).scheme != "https":
            messages.append(
                Error(
                    "AWS_S3_ENDPOINT_URL must use HTTPS in production.",
                    id="inventory.E014",
                )
            )

        if not getattr(settings, "AWS_S3_USE_SSL", True):
            messages.append(
                Error(
                    "AWS_S3_USE_SSL must be enabled in production.",
                    id="inventory.E015",
                )
            )

        if not getattr(settings, "AWS_S3_VERIFY", True):
            messages.append(
                Error(
                    "AWS_S3_VERIFY must be enabled in production.",
                    id="inventory.E016",
                )
            )

    return messages

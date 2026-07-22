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

    if settings.IMPORT_TASK_SOFT_TIME_LIMIT >= settings.IMPORT_TASK_TIME_LIMIT:
        messages.append(
            Error(
                "IMPORT_TASK_SOFT_TIME_LIMIT must be lower than "
                "IMPORT_TASK_TIME_LIMIT.",
                id="inventory.E017",
            )
        )

    if settings.REPORT_TASK_SOFT_TIME_LIMIT >= settings.REPORT_TASK_TIME_LIMIT:
        messages.append(
            Error(
                "REPORT_TASK_SOFT_TIME_LIMIT must be lower than "
                "REPORT_TASK_TIME_LIMIT.",
                id="inventory.E018",
            )
        )

    longest_lease_interval = max(
        settings.IMPORT_TASK_TIME_LIMIT,
        settings.REPORT_TASK_TIME_LIMIT,
        settings.TASK_RETRY_MAX_DELAY_SECONDS,
    )
    if settings.JOB_STALE_AFTER_SECONDS <= longest_lease_interval:
        messages.append(
            Error(
                "JOB_STALE_AFTER_SECONDS must exceed every job hard time "
                "limit and the maximum retry delay so recovery cannot take "
                "over active or scheduled work.",
                id="inventory.E019",
            )
        )

    if (
        settings.TASK_RETRY_BASE_DELAY_SECONDS <= 0
        or settings.TASK_RETRY_MAX_DELAY_SECONDS
        < settings.TASK_RETRY_BASE_DELAY_SECONDS
    ):
        messages.append(
            Error(
                "Task retry delays must be positive and the maximum delay "
                "must not be lower than the base delay.",
                id="inventory.E021",
            )
        )

    minimum_attempts = max(
        settings.IMPORT_TASK_MAX_RETRIES,
        settings.REPORT_TASK_MAX_RETRIES,
    ) + 1
    if settings.JOB_MAX_ATTEMPTS < minimum_attempts:
        messages.append(
            Error(
                "JOB_MAX_ATTEMPTS must allow the initial delivery plus all "
                f"configured Celery retries ({minimum_attempts}).",
                id="inventory.E022",
            )
        )

    required_routes = {
        "data_import.tasks.*": "imports",
        "reporting.tasks.*": "reports",
        "core.tasks.job_recovery.*": "maintenance",
    }
    configured_routes = getattr(settings, "CELERY_TASK_ROUTES", {})
    invalid_routes = [
        task_pattern
        for task_pattern, expected_queue in required_routes.items()
        if configured_routes.get(task_pattern, {}).get("queue")
        != expected_queue
    ]
    if invalid_routes:
        messages.append(
            Error(
                "Required Celery task routes are missing or incorrect: "
                + ", ".join(invalid_routes),
                id="inventory.E020",
            )
        )

    return messages

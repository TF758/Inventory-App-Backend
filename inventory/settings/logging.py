# inventory/settings/logging.py

from pathlib import Path

from .base import env, IS_TESTING, LOG_TO_CONSOLE


# -------------------------------------------------
# Core logging settings
# -------------------------------------------------

LOG_LEVEL = env(
    "LOG_LEVEL",
    default="INFO",
)

SERVICE_NAME = env(
    "SERVICE_NAME",
    default="app",
)

# Parallel test workers must not share rotating file handlers. Tests also
# intentionally exercise error paths, so suppress application logging there.
if IS_TESTING:
    LOG_TO_CONSOLE = False
    LOG_TO_FILE = False
else:
    LOG_TO_FILE = env.bool(
        "LOG_TO_FILE",
        default=True,
    )

LOG_FORMAT = env(
    "LOG_FORMAT",
    default="text",
).lower()

LOG_FORMATTER = "json" if LOG_FORMAT == "json" else "detailed"


# -------------------------------------------------
# Log file rotation settings
# -------------------------------------------------

LOG_FILE_WHEN = env(
    "LOG_FILE_WHEN",
    default="midnight",
)

LOG_FILE_INTERVAL = env.int(
    "LOG_FILE_INTERVAL",
    default=1,
)

LOG_FILE_BACKUP_COUNT = env.int(
    "LOG_FILE_BACKUP_COUNT",
    default=30,
)

LOG_ERROR_WHEN = env(
    "LOG_ERROR_WHEN",
    default="midnight",
)

LOG_ERROR_INTERVAL = env.int(
    "LOG_ERROR_INTERVAL",
    default=1,
)

LOG_ERROR_BACKUP_COUNT = env.int(
    "LOG_ERROR_BACKUP_COUNT",
    default=30,
)


# -------------------------------------------------
# Log archive and cleanup settings
# -------------------------------------------------

LOG_ARCHIVE_AFTER_DAYS = env.int(
    "LOG_ARCHIVE_AFTER_DAYS",
    default=7,
)

LOG_DELETE_AFTER_DAYS = env.int(
    "LOG_DELETE_AFTER_DAYS",
    default=7,
)

LOG_ARCHIVE_CRON = env(
    "LOG_ARCHIVE_CRON",
    default="15 2 * * *",
)


# -------------------------------------------------
# Logs directory
# -------------------------------------------------

LOGS_DIR = Path("/var/log/inventory")

if LOG_TO_FILE:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# Handler definitions
# -------------------------------------------------

handlers = {}

if LOG_TO_CONSOLE:
    handlers["console"] = {
        "class": "logging.StreamHandler",
        "level": LOG_LEVEL,
        "formatter": LOG_FORMATTER,
        "filters": ["request_id"],
    }

if LOG_TO_FILE:
    handlers["file"] = {
        "class": "logging.handlers.TimedRotatingFileHandler",
        "filename": str(LOGS_DIR / f"{SERVICE_NAME}.log"),
        "when": LOG_FILE_WHEN,
        "interval": LOG_FILE_INTERVAL,
        "backupCount": LOG_FILE_BACKUP_COUNT,
        "level": LOG_LEVEL,
        "formatter": LOG_FORMATTER,
        "filters": ["request_id"],
        "encoding": "utf-8",
    }

    handlers["error_file"] = {
        "class": "logging.handlers.TimedRotatingFileHandler",
        "filename": str(LOGS_DIR / f"{SERVICE_NAME}.error.log"),
        "when": LOG_ERROR_WHEN,
        "interval": LOG_ERROR_INTERVAL,
        "backupCount": LOG_ERROR_BACKUP_COUNT,
        "level": "ERROR",
        "formatter": LOG_FORMATTER,
        "filters": ["request_id"],
        "encoding": "utf-8",
    }

# Safety fallback:
# Prevent Django from starting with an invalid empty handlers config.
if not handlers:
    handlers["null"] = {
        "class": "logging.NullHandler",
    }


# -------------------------------------------------
# Handler groups
# -------------------------------------------------

app_handlers = [
    handler_name
    for handler_name in ["console", "file", "error_file", "null"]
    if handler_name in handlers
]

error_handlers = [
    handler_name
    for handler_name in ["console", "error_file", "null"]
    if handler_name in handlers
]


# -------------------------------------------------
# Logging configuration
# -------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "detailed": {
            "()": "core.logging.SafeExtraFormatter",
            "format": (
                "%(asctime)s | %(levelname)s | %(name)s | "
                "%(filename)s:%(lineno)d (%(funcName)s) | "
                "%(message)s | service=%(service_name)s | request_id=%(request_id)s"
            ),
        },

        "json": {
            "()": "core.logging.JsonFormatter",
        },
    },

    "filters": {
        "request_id": {
            "()": "core.logging.RequestIDFilter",
        },
    },

    "handlers": handlers,

    "loggers": {
        "arms": {
            "handlers": app_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "django": {
            "handlers": app_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "django.request": {
            "handlers": error_handlers,
            "level": "ERROR",
            "propagate": False,
        },

        "django.server": {
            "handlers": error_handlers,
            "level": "ERROR",
            "propagate": False,
        },

        "django.db.backends": {
            "handlers": error_handlers,
            "level": "ERROR",
            "propagate": False,
        },

        "daphne": {
            "handlers": app_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "celery": {
            "handlers": app_handlers,
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },

    "root": {
        "handlers": app_handlers,
        "level": LOG_LEVEL,
    },
}
# inventory/settings/logging.py

from pathlib import Path
from .base import env, BASE_DIR, LOG_TO_CONSOLE

LOG_LEVEL = env(
    "LOG_LEVEL",
    default="INFO",
)

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

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

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
                "%(message)s | request_id=%(request_id)s"
            ),
        },
    },

    "filters": {
        "request_id": {
            "()": "core.logging.RequestIDFilter",
        },
    },

    "handlers": {
        **({
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "filters": ["request_id"],
            }
        } if LOG_TO_CONSOLE else {}),

        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "app.log"),
            "when": LOG_FILE_WHEN,
            "interval": LOG_FILE_INTERVAL,
            "backupCount": LOG_FILE_BACKUP_COUNT,
            "level": LOG_LEVEL,
            "formatter": "detailed",
            "filters": ["request_id"],
            "encoding": "utf-8",
        },

        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOGS_DIR / "error.log"),
            "when": LOG_ERROR_WHEN,
            "interval": LOG_ERROR_INTERVAL,
            "backupCount": LOG_ERROR_BACKUP_COUNT,
            "level": "ERROR",
            "formatter": "detailed",
            "filters": ["request_id"],
            "encoding": "utf-8",
        },
    },

    "loggers": {
        "arms": {
            "handlers": ["file", "error_file"] + (["console"] if LOG_TO_CONSOLE else []),
            "level": LOG_LEVEL,
            "propagate": False,
        },

        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },

    "root": {
        "handlers": ["file", "error_file"],
        "level": LOG_LEVEL,
    },
}
# inventory/settings/scheduled_tasks.py

from .base import env

# -------------------------------------------------
# Notification schedules
# -------------------------------------------------

NOTIF_AUTO_READ_CRON = env(
    "NOTIF_AUTO_READ_CRON",
    default="0 2 * * *",
)

NOTIF_SOFT_DELETE_CRON = env(
    "NOTIF_SOFT_DELETE_CRON",
    default="15 2 * * *",
)

NOTIF_CLEANUP_CRON = env(
    "NOTIF_CLEANUP_CRON",
    default="30 2 * * *",
)

# -------------------------------------------------
# Report cleanup
# -------------------------------------------------

TASKRUN_CLEANUP_CRON = env(
    "TASKRUN_CLEANUP_CRON",
    default="0 12 * * *",
)

# -------------------------------------------------
# Analytics snapshots
# -------------------------------------------------

DAILY_SYSTEM_METRICS_CRON = env(
    "DAILY_SYSTEM_METRICS_CRON",
    default="0 2 * * *",
)

# -------------------------------------------------
# User session maintenance
# -------------------------------------------------

USERSESSION_CLEANUP_CRON = env(
    "USERSESSION_CLEANUP_CRON",
    default="40 12 * * *",
)

USERSESSION_EXPIRE_CRON = env(
    "USERSESSION_EXPIRE_CRON",
    default="15 * * * *",
)

# -------------------------------------------------
# ScheduledTaskRun retention
# -------------------------------------------------

TASKRUN_SUCCESS_RETENTION_DAYS = env.int(
    "TASKRUN_SUCCESS_RETENTION_DAYS",
    default=7,
)

TASKRUN_SKIPPED_RETENTION_DAYS = env.int(
    "TASKRUN_SKIPPED_RETENTION_DAYS",
    default=14,
)

TASKRUN_FAILED_RETENTION_DAYS = env.int(
    "TASKRUN_FAILED_RETENTION_DAYS",
    default=90,
)

# -------------------------------------------------
# Log maintenance
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
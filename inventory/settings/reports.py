# inventory/settings/reports.py

from .base import BASE_DIR, env

REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

REPORT_RETENTION_DAYS = env.int(
    "REPORT_RETENTION_DAYS",
    default=30,
)

REPORT_DELETE_CRON = env(
    "TASKRUN_CLEANUP_CRON",
    default="0 12 * * *",
)

REPORT_FILENAME_TEMPLATE = (
    "{report_type}-{public_id}"
)

REPORT_CACHE_TTL_SECONDS = env.int(
    "REPORT_CACHE_TTL_SECONDS",
    default=900,
)
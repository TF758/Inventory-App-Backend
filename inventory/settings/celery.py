from .base import env
from .redis import REDIS_CELERY_URL

CELERY_BROKER_URL = REDIS_CELERY_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Long-running import and report jobs must only be acknowledged after they
# finish. If a worker process is lost, the broker can redeliver the message and
# the database-backed job lease prevents concurrent duplicate execution.
CELERY_WORKER_CANCEL_LONG_RUNNING_TASKS_ON_CONNECTION_LOSS = True
CELERY_WORKER_PREFETCH_MULTIPLIER = env.int(
    "CELERY_WORKER_PREFETCH_MULTIPLIER",
    default=1,
)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_CREATE_MISSING_QUEUES = True

CELERY_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "data_import.tasks.*": {"queue": "imports"},
    "reporting.tasks.*": {"queue": "reports"},
    "core.tasks.cleanup.*": {"queue": "maintenance"},
    "core.tasks.job_recovery.*": {"queue": "maintenance"},
    "core.tasks.logs.*": {"queue": "maintenance"},
    "analytics.tasks.cleanup.*": {"queue": "maintenance"},
    "analytics.tasks.snapshots.*": {"queue": "maintenance"},
    "agreements.tasks.*": {"queue": "maintenance"},
}

IMPORT_TASK_SOFT_TIME_LIMIT = env.int(
    "IMPORT_TASK_SOFT_TIME_LIMIT",
    default=1500,
)
IMPORT_TASK_TIME_LIMIT = env.int(
    "IMPORT_TASK_TIME_LIMIT",
    default=1800,
)
IMPORT_TASK_MAX_RETRIES = env.int(
    "IMPORT_TASK_MAX_RETRIES",
    default=2,
)

REPORT_TASK_SOFT_TIME_LIMIT = env.int(
    "REPORT_TASK_SOFT_TIME_LIMIT",
    default=1500,
)
REPORT_TASK_TIME_LIMIT = env.int(
    "REPORT_TASK_TIME_LIMIT",
    default=1800,
)
REPORT_TASK_MAX_RETRIES = env.int(
    "REPORT_TASK_MAX_RETRIES",
    default=2,
)

TASK_RETRY_BASE_DELAY_SECONDS = env.int(
    "TASK_RETRY_BASE_DELAY_SECONDS",
    default=15,
)
TASK_RETRY_MAX_DELAY_SECONDS = env.int(
    "TASK_RETRY_MAX_DELAY_SECONDS",
    default=300,
)

JOB_STALE_AFTER_SECONDS = env.int(
    "JOB_STALE_AFTER_SECONDS",
    default=2100,
)
JOB_DISPATCH_GRACE_SECONDS = env.int(
    "JOB_DISPATCH_GRACE_SECONDS",
    default=120,
)
JOB_MAX_ATTEMPTS = env.int(
    "JOB_MAX_ATTEMPTS",
    default=3,
)
JOB_RECOVERY_CRON = env(
    "JOB_RECOVERY_CRON",
    default="*/5 * * * *",
)

MAINTENANCE_TASK_SOFT_TIME_LIMIT = env.int(
    "MAINTENANCE_TASK_SOFT_TIME_LIMIT",
    default=300,
)
MAINTENANCE_TASK_TIME_LIMIT = env.int(
    "MAINTENANCE_TASK_TIME_LIMIT",
    default=360,
)

from .redis import REDIS_CELERY_URL

CELERY_BROKER_URL = REDIS_CELERY_URL

CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_BACKEND = "django-db"

CELERY_BEAT_SCHEDULER = (
    "django_celery_beat.schedulers:"
    "DatabaseScheduler"
)
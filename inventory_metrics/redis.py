import redis
from django.conf import settings

redis_reports_client = redis.Redis.from_url(
    settings.REDIS_REPORTS_URL,
    decode_responses=False,
)

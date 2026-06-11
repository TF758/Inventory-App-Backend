from .base import env, IS_TESTING

REDIS_HOST = env(
    "REDIS_HOST",
    default="redis"
)

REDIS_PORT = env.int(
    "REDIS_PORT",
    default=6379
)

REDIS_DB_CELERY = env.int(
    "REDIS_DB_CELERY",
    default=0,
)

REDIS_DB_CHANNELS = env.int(
    "REDIS_DB_CHANNELS",
    default=1,
)

REDIS_DB_REPORTS = env.int(
    "REDIS_DB_REPORTS",
    default=2,
)

REDIS_BASE_URL = (
    f"redis://{REDIS_HOST}:{REDIS_PORT}"
)

REDIS_CELERY_URL = (
    f"{REDIS_BASE_URL}/{REDIS_DB_CELERY}"
)

REDIS_CHANNELS_URL = (
    f"{REDIS_BASE_URL}/{REDIS_DB_CHANNELS}"
)

REDIS_REPORTS_URL = (
    f"{REDIS_BASE_URL}/{REDIS_DB_REPORTS}"
)

if IS_TESTING:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND":
                "channels.layers.InMemoryChannelLayer",
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND":
                "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_CHANNELS_URL],
            },
        }
    }
from .base import env, IS_TESTING


REDIS_HOST = env(
    "REDIS_HOST",
    default="redis",
)

REDIS_PORT = env.int(
    "REDIS_PORT",
    default=6379,
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

REDIS_DB_CACHE = env.int(
    "REDIS_DB_CACHE",
    default=3,
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

REDIS_CACHE_URL = (
    f"{REDIS_BASE_URL}/{REDIS_DB_CACHE}"
)


# -------------------------------------------------
# Django application cache
# -------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": (
            "django.core.cache.backends.redis.RedisCache"
        ),
        "LOCATION": REDIS_CACHE_URL,
        "KEY_PREFIX": "arms",
        "TIMEOUT": 1800,
    },
    # Analytics stays isolated in the existing reports Redis database while
    # using Django's cache API for native serialization and fail-open handling.
    "reports": {
        "BACKEND": (
            "django.core.cache.backends.redis.RedisCache"
        ),
        "LOCATION": REDIS_REPORTS_URL,
        "KEY_PREFIX": "arms:analytics",
        "TIMEOUT": 86400,
    },
}

ANALYTICS_CACHE_ALIAS = env(
    "ANALYTICS_CACHE_ALIAS",
    default="reports",
)

# Generations control freshness. TTL primarily reclaims unreachable old keys.
ANALYTICS_CACHE_TIMEOUT = env.int(
    "ANALYTICS_CACHE_TIMEOUT",
    default=86400,
)

ANALYTICS_CACHE_LOCK_TIMEOUT = env.int(
    "ANALYTICS_CACHE_LOCK_TIMEOUT",
    default=30,
)

ANALYTICS_CACHE_LOCK_WAIT_MS = env.int(
    "ANALYTICS_CACHE_LOCK_WAIT_MS",
    default=200,
)


SITES_OPTION_CACHE_ALIAS = "default"

SITES_OPTION_CACHE_TIMEOUT = env.int(
    "SITES_OPTION_CACHE_TIMEOUT",
    default=1800,
)

SITES_OPTION_CACHE_DEBUG_HEADERS = env.bool(
    "SITES_OPTION_CACHE_DEBUG_HEADERS",
    default=False,
)


# -------------------------------------------------
# Channels
# -------------------------------------------------

if IS_TESTING:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": (
                "channels.layers.InMemoryChannelLayer"
            ),
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": (
                "channels_redis.core.RedisChannelLayer"
            ),
            "CONFIG": {
                "hosts": [
                    REDIS_CHANNELS_URL,
                ],
                "prefix": "arms:channels",
            },
        },
    }

# -------------------------------------------------
# User + active-role scoped list cache
# -------------------------------------------------

# Uses the Django application cache (Redis DB 3 by default).
USER_SCOPE_CACHE_ALIAS = env(
    "USER_SCOPE_CACHE_ALIAS",
    default="default",
)

# The global site-options generation uses the same Redis cache by default.
SITE_OPTION_CACHE_ALIAS = env(
    "SITE_OPTION_CACHE_ALIAS",
    default=USER_SCOPE_CACHE_ALIAS,
)

# Intentionally short-lived. Per-viewset values may still override this,
# although the option viewsets now use this shared setting directly.
USER_SCOPE_CACHE_TIMEOUT = env.int(
    "USER_SCOPE_CACHE_TIMEOUT",
    default=120,
)

# Keeps a lightweight marker after the response expires so logs can distinguish
# an initial cold miss from a genuine expiry/rebuild.
USER_SCOPE_CACHE_MARKER_GRACE = env.int(
    "USER_SCOPE_CACHE_MARKER_GRACE",
    default=300,
)

USER_SCOPE_CACHE_DEBUG_HEADERS = env.bool(
    "USER_SCOPE_CACHE_DEBUG_HEADERS",
    default=True,
)

USER_SCOPE_CACHE_COUNT_DB_QUERIES = env.bool(
    "USER_SCOPE_CACHE_COUNT_DB_QUERIES",
    default=True,
)

# Verbose development logging of canonical query parameters. Disable in
# production if search text or filters should not appear in application logs.
USER_SCOPE_CACHE_LOG_REQUEST_PARAMS = env.bool(
    "USER_SCOPE_CACHE_LOG_REQUEST_PARAMS",
    default=True,
)

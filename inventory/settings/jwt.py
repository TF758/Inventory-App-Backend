from datetime import timedelta
from .base import env

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int(
            "JWT_ACCESS_MINUTES",
            default=15,
        )
    ),

    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int(
            "JWT_REFRESH_DAYS",
            default=1,
        )
    ),

    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,

    "USER_ID_FIELD": "public_id",
    "USER_ID_CLAIM": "public_id",

    "UPDATE_LAST_LOGIN": True,

    "AUTH_HEADER_TYPES": ("Bearer",),
}
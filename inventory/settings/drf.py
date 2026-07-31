from .base import APP_ENV, IS_TESTING, env


ENABLE_BASIC_AUTH = env.bool(
    "ENABLE_BASIC_AUTH",
    default=APP_ENV in {"dev", "local"},
)

authentication_classes = [
    "core.authentication.SessionJWTAuthentication",
    "rest_framework_simplejwt.authentication.JWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
]

if ENABLE_BASIC_AUTH:
    authentication_classes.append(
        "rest_framework.authentication.BasicAuthentication"
    )

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS":
        "core.pagination.OptionalPagination",

    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],

    "DEFAULT_AUTHENTICATION_CLASSES": authentication_classes,

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],

    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="100/hour"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "login": env("THROTTLE_LOGIN", default="5/min"),
        "token_refresh": env("THROTTLE_REFRESH", default="30/min"),
        "password_reset": env(
            "THROTTLE_PASSWORD_RESET",
            default="3/hour",
        ),
        "user_read": env("THROTTLE_USER_READ", default="1000/hour"),
        "equipment_action": env(
            "THROTTLE_EQUIPMENT",
            default="30/hour",
        ),
        "admin_action": env("THROTTLE_ADMIN", default="100/hour"),
    },

    "DEFAULT_SCHEMA_CLASS":
        "drf_spectacular.openapi.AutoSchema",
}

if IS_TESTING:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

SPECTACULAR_SETTINGS = {
    "TITLE": "ARMS Platform API",
    "DESCRIPTION":
        "Asset, inventory, reporting and operations API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

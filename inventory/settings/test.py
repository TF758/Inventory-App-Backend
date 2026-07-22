from . import *

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Tests run under a dedicated non-development settings module. Keep
# development-only authentication shortcuts disabled regardless of values
# loaded from a local development environment file.
APP_ENV = "test"
ENABLE_BASIC_AUTH = False
WEBSOCKET_ALLOW_QUERY_TOKEN = False
API_DOCS_ENABLED = False
API_DOCS_PUBLIC = False
METRICS_ALLOW_PUBLIC = False

basic_authentication_class = (
    "rest_framework.authentication.BasicAuthentication"
)
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    authentication_class
    for authentication_class in REST_FRAMEWORK[
        "DEFAULT_AUTHENTICATION_CLASSES"
    ]
    if authentication_class != basic_authentication_class
]

# Keep test and CI file operations isolated from developer worktrees and
# container-local paths while exercising the same named storage aliases used
# by production code.
STORAGE_BACKEND = "memory"
STORAGE_SHARED = True
STORAGE_IS_DISTRIBUTED = False
STORAGE_IS_SHARED = True
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "reports": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}

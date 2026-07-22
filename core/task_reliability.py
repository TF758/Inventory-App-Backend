import uuid

from billiard.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import InterfaceError, OperationalError
from kombu.exceptions import OperationalError as KombuOperationalError
from redis.exceptions import RedisError


TRANSIENT_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    InterfaceError,
    OperationalError,
    KombuOperationalError,
    RedisError,
    SoftTimeLimitExceeded,
)

try:
    from botocore.exceptions import (
        ConnectionClosedError,
        ConnectTimeoutError,
        EndpointConnectionError,
        ReadTimeoutError,
    )
except ImportError:  # pragma: no cover - S3 support is optional at runtime.
    S3_TRANSIENT_EXCEPTIONS = ()
else:
    S3_TRANSIENT_EXCEPTIONS = (
        ConnectionClosedError,
        ConnectTimeoutError,
        EndpointConnectionError,
        ReadTimeoutError,
    )


def request_task_id(task) -> str:
    request_id = getattr(getattr(task, "request", None), "id", None)
    return request_id or f"local-{uuid.uuid4().hex}"


def request_is_redelivered(task) -> bool:
    request = getattr(task, "request", None)
    delivery_info = getattr(request, "delivery_info", {})
    return bool((delivery_info or {}).get("redelivered", False))


def is_transient_task_error(exc: Exception) -> bool:
    return isinstance(exc, TRANSIENT_EXCEPTIONS + S3_TRANSIENT_EXCEPTIONS)


def retry_countdown(task) -> int:
    retries = int(getattr(getattr(task, "request", None), "retries", 0) or 0)
    base = settings.TASK_RETRY_BASE_DELAY_SECONDS
    maximum = settings.TASK_RETRY_MAX_DELAY_SECONDS
    return min(base * (2 ** retries), maximum)

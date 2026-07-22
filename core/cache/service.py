# sites/cache/service.py

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from django.conf import settings
from django.core.cache import cache




T = TypeVar("T")

CACHE_MISSING = object()


def get_sites_cache_timeout() -> int:
    return getattr(
        settings,
        "SITES_CACHE_TIMEOUT",
        60 * 60,
    )


def cached_site_value(
    *,
    key: str,
    buckets: Iterable[str],
    loader: Callable[[], T],
    timeout: int | None = None,
) -> tuple[T, bool]:
    """
    Return (value, cache_hit).

    Empty lists, dictionaries, zero, False and None are all valid
    cached values.
    """
    cached_value = cache.get(key, CACHE_MISSING)

    if cached_value is not CACHE_MISSING:
        return cached_value, True

    value = loader()

    cache.set(
        key,
        value,
        timeout=(
            timeout
            if timeout is not None
            else get_sites_cache_timeout()
        ),
    )

    return value, False
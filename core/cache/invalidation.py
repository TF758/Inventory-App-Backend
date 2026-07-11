# sites/cache/invalidation.py

from __future__ import annotations

import logging
from collections.abc import Iterable

from django.conf import settings
from django.core.cache import caches
from django.db import transaction


logger = logging.getLogger("sites.cache")

VALID_OPTION_NAMESPACES = {
    "departments",
    "locations",
    "rooms",
}


def get_option_cache():
    alias = getattr(
        settings,
        "SITES_OPTION_CACHE_ALIAS",
        "default",
    )
    return caches[alias]


def version_key(namespace: str) -> str:
    return f"sites:options:version:{namespace}"


def invalidate_option_namespaces(
    namespaces: Iterable[str],
    *,
    reason: str,
) -> None:
    namespaces = set(namespaces)

    invalid_namespaces = (
        namespaces - VALID_OPTION_NAMESPACES
    )

    if invalid_namespaces:
        raise ValueError(
            "Invalid site option namespaces: "
            f"{sorted(invalid_namespaces)}"
        )

    logger.info(
        "[SITES CACHE] INVALIDATION_QUEUED namespaces=%s reason=%s",
        sorted(namespaces),
        reason,
    )

    def invalidate() -> None:
        cache = get_option_cache()

        for namespace in sorted(namespaces):
            key = version_key(namespace)
            old_version = int(cache.get(key, 1) or 1)

            created = cache.add(
                key,
                2,
                timeout=None,
            )

            if created:
                new_version = 2
            else:
                try:
                    new_version = int(cache.incr(key))
                except ValueError:
                    new_version = old_version + 1
                    cache.set(
                        key,
                        new_version,
                        timeout=None,
                    )

            logger.warning(
                "[SITES CACHE] INVALIDATE "
                "namespace=%s old_version=%s new_version=%s reason=%s",
                namespace,
                old_version,
                new_version,
                reason,
            )

    transaction.on_commit(invalidate)
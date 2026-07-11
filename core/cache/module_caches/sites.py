# sites/cache/options.py

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from django.conf import settings
from django.core.cache import caches
from django.db import transaction


OPTION_NAMESPACES = {
    "departments",
    "locations",
    "rooms",
}

OPTION_CACHE_SCHEMA_VERSION = 1

OPTION_CACHE_MISSING = object()


def get_option_cache():
    alias = getattr(
        settings,
        "SITES_OPTION_CACHE_ALIAS",
        "default",
    )
    return caches[alias]


def get_option_cache_timeout() -> int:
    return getattr(
        settings,
        "SITES_OPTION_CACHE_TIMEOUT",
        60 * 30,
    )


def _version_key(namespace: str) -> str:
    return f"sites:options:version:{namespace}"


def _metric_key(namespace: str, event: str) -> str:
    return f"sites:options:metrics:{namespace}:{event}"


def get_option_cache_version(namespace: str) -> int:
    if namespace not in OPTION_NAMESPACES:
        raise ValueError(f"Unknown option-cache namespace: {namespace}")

    cache = get_option_cache()
    key = _version_key(namespace)

    version = cache.get(key)

    if version is not None:
        return int(version)

    # cache.add() is atomic for supported cache backends.
    cache.add(key, 1, timeout=None)

    return int(cache.get(key, 1))


def normalize_query_params(request) -> list[tuple[str, str]]:
    """
    Normalize query parameters so parameter ordering does not create
    different cache keys.

    Includes search, filtering, pagination, page size and format.
    """
    normalized: list[tuple[str, str]] = []

    for name in sorted(request.query_params.keys()):
        values = sorted(request.query_params.getlist(name))

        for value in values:
            normalized.append((name, value))

    return normalized


def get_request_scope_fingerprint(request) -> dict:
    """
    Initially isolate cached options per user.

    active_role_id is available directly on the User instance and does
    not require loading the related RoleAssignment object.
    """
    user = request.user

    return {
        "user_id": user.pk,
        "active_role_id": getattr(user, "active_role_id", None),
        "legacy_role": getattr(user, "role", ""),
        "is_superuser": bool(user.is_superuser),
    }


def build_option_cache_key(
    *,
    namespace: str,
    request,
) -> str:
    payload = {
        "namespace": namespace,
        "namespace_version": get_option_cache_version(namespace),
        "schema_version": OPTION_CACHE_SCHEMA_VERSION,
        "scope": get_request_scope_fingerprint(request),
        "query": normalize_query_params(request),
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    digest = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:32]

    return (
        f"sites:options:{namespace}:"
        f"v{payload['namespace_version']}:"
        f"s{OPTION_CACHE_SCHEMA_VERSION}:"
        f"{digest}"
    )


def record_option_cache_event(
    namespace: str,
    event: str,
) -> None:
    """
    Lightweight counters for the initial rollout.

    A miss means that the option list proceeds to the normal queryset
    and serialization path.
    """
    cache = get_option_cache()
    key = _metric_key(namespace, event)

    try:
        created = cache.add(key, 1, timeout=None)

        if not created:
            cache.incr(key)
    except Exception:
        # Metrics must never break an endpoint.
        pass


def get_option_cache_stats() -> dict[str, dict[str, int]]:
    cache = get_option_cache()

    return {
        namespace: {
            event: int(
                cache.get(
                    _metric_key(namespace, event),
                    0,
                )
                or 0
            )
            for event in ("hit", "miss", "error")
        }
        for namespace in sorted(OPTION_NAMESPACES)
    }


def invalidate_option_namespaces(
    *namespaces: str,
) -> None:
    """
    Bump namespace versions after the current transaction commits.

    Existing cache entries become unreachable and expire naturally.
    This avoids maintaining an ever-growing registry of concrete keys.
    """
    invalid_namespaces = (
        set(namespaces) - OPTION_NAMESPACES
    )

    if invalid_namespaces:
        raise ValueError(
            "Unknown option-cache namespaces: "
            f"{sorted(invalid_namespaces)}"
        )

    def bump_versions() -> None:
        cache = get_option_cache()

        for namespace in set(namespaces):
            key = _version_key(namespace)

            try:
                created = cache.add(
                    key,
                    2,
                    timeout=None,
                )

                if not created:
                    cache.incr(key)

            except ValueError:
                # The key may have expired between add() and incr().
                cache.set(key, 2, timeout=None)

            except Exception:
                # Invalidation failure should be logged eventually,
                # but should not roll back a successful model mutation.
                continue

    transaction.on_commit(bump_versions)
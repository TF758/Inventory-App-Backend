"""Shared, versioned caching for analytics query results.

This module deliberately does not know anything about request users or API
responses. Views must perform authentication/authorization before calling the
analytics builders. Cached values are shared because snapshot-backed analytics
are the same for every authorized caller.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from django.conf import settings
from django.core.cache import caches
from django.db import transaction


logger = logging.getLogger("analytics.cache")

T = TypeVar("T")
_CACHE_MISSING = object()

SYSTEM_METRICS = "system_metrics"
AUTH_METRICS = "auth_metrics"
RETURN_METRICS = "return_metrics"
DEPARTMENT_SNAPSHOTS = "department_snapshots"

_VALID_DEPENDENCIES = {
    SYSTEM_METRICS,
    AUTH_METRICS,
    RETURN_METRICS,
    DEPARTMENT_SNAPSHOTS,
}


@dataclass(frozen=True, slots=True)
class AnalyticsCacheDependency:
    namespace: str
    identity: str = "global"

    def __post_init__(self) -> None:
        if self.namespace not in _VALID_DEPENDENCIES:
            raise ValueError(
                f"Unknown analytics cache dependency: {self.namespace}"
            )
        if not str(self.identity).strip():
            raise ValueError("Analytics cache dependency identity is required")


class AnalyticsCacheService:
    """Cache analytics values while keeping Redis an optional optimisation."""

    KEY_PREFIX = "analytics-query-cache:v1"
    CACHE_SCHEMA_VERSION = 1

    @classmethod
    def get_cache_alias(cls) -> str:
        return str(getattr(settings, "ANALYTICS_CACHE_ALIAS", "default"))

    @classmethod
    def get_cache(cls):
        return caches[cls.get_cache_alias()]

    @classmethod
    def get_timeout(cls) -> int:
        timeout = int(getattr(settings, "ANALYTICS_CACHE_TIMEOUT", 24 * 60 * 60))
        if timeout <= 0:
            raise ValueError("ANALYTICS_CACHE_TIMEOUT must be greater than zero")
        return timeout

    @classmethod
    def get_lock_timeout(cls) -> int:
        return max(
            1,
            int(getattr(settings, "ANALYTICS_CACHE_LOCK_TIMEOUT", 30)),
        )

    @classmethod
    def get_lock_wait_ms(cls) -> int:
        return max(
            0,
            int(getattr(settings, "ANALYTICS_CACHE_LOCK_WAIT_MS", 200)),
        )

    @classmethod
    def generation_key(cls, dependency: AnalyticsCacheDependency) -> str:
        return (
            f"{cls.KEY_PREFIX}:generation:"
            f"{dependency.namespace}:{dependency.identity}"
        )

    @classmethod
    def get_generation(
        cls,
        dependency: AnalyticsCacheDependency,
    ) -> int:
        cache = cls.get_cache()
        key = cls.generation_key(dependency)
        value = cache.get(key)

        if value is not None:
            return int(value)

        cache.add(key, 1, timeout=None)
        return int(cache.get(key, 1) or 1)

    @classmethod
    def bump_generation(
        cls,
        dependency: AnalyticsCacheDependency,
        *,
        reason: str,
    ) -> None:
        cache = cls.get_cache()
        key = cls.generation_key(dependency)

        try:
            created = cache.add(key, 2, timeout=None)
            if created:
                new_generation = 2
            else:
                new_generation = int(cache.incr(key))
        except ValueError:
            cache.set(key, 2, timeout=None)
            new_generation = 2

        logger.info(
            "ANALYTICS CACHE INVALIDATED | namespace=%s identity=%s "
            "generation=%s reason=%s",
            dependency.namespace,
            dependency.identity,
            new_generation,
            reason,
        )

    @classmethod
    def invalidate_on_commit(
        cls,
        *dependencies: AnalyticsCacheDependency,
        reason: str,
    ) -> None:
        unique_dependencies = tuple(dict.fromkeys(dependencies))

        def invalidate() -> None:
            for dependency in unique_dependencies:
                try:
                    cls.bump_generation(dependency, reason=reason)
                except Exception:
                    # The database write has succeeded already. A cache failure
                    # must not convert it into an application failure.
                    logger.exception(
                        "ANALYTICS CACHE INVALIDATION FAILED | "
                        "namespace=%s identity=%s reason=%s",
                        dependency.namespace,
                        dependency.identity,
                        reason,
                    )

        transaction.on_commit(invalidate)

    @classmethod
    def _canonical_digest(cls, value: Any) -> str:
        serialized = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def build_result_key(
        cls,
        *,
        scope: str,
        identity: str,
        section: str,
        dimensions: Mapping[str, Any],
        dependency_generations: Sequence[tuple[str, str, int]],
    ) -> str:
        snapshot_schema_version = int(
            getattr(settings, "SNAPSHOT_SCHEMA_VERSION", 1)
        )
        generation_digest = cls._canonical_digest(dependency_generations)
        dimensions_digest = cls._canonical_digest(dict(dimensions))

        return (
            f"{cls.KEY_PREFIX}:result:"
            f"scope={scope}:identity={identity}:section={section}:"
            f"cache-schema={cls.CACHE_SCHEMA_VERSION}:"
            f"snapshot-schema={snapshot_schema_version}:"
            f"generations={generation_digest}:dimensions={dimensions_digest}"
        )

    @classmethod
    def _read(cls, cache, key: str):
        return cache.get(key, _CACHE_MISSING)

    @classmethod
    def get_or_build(
        cls,
        *,
        scope: str,
        identity: str,
        section: str,
        dimensions: Mapping[str, Any],
        dependencies: Sequence[AnalyticsCacheDependency],
        builder: Callable[[], T],
    ) -> T:
        """Return a cached value or execute ``builder``.

        Empty lists, dictionaries, zero, False and None are valid cached values.
        Any cache backend failure falls back to the builder and never changes
        the public API response.
        """

        try:
            cache = cls.get_cache()
            dependency_generations = [
                (
                    dependency.namespace,
                    dependency.identity,
                    cls.get_generation(dependency),
                )
                for dependency in dependencies
            ]
            key = cls.build_result_key(
                scope=scope,
                identity=identity,
                section=section,
                dimensions=dimensions,
                dependency_generations=dependency_generations,
            )
            cached = cls._read(cache, key)
        except Exception:
            logger.exception(
                "ANALYTICS CACHE BYPASS | scope=%s identity=%s section=%s "
                "reason=read_or_generation_failed",
                scope,
                identity,
                section,
            )
            return builder()

        if cached is not _CACHE_MISSING:
            logger.debug(
                "ANALYTICS CACHE HIT | scope=%s identity=%s section=%s",
                scope,
                identity,
                section,
            )
            return cached

        lock_key = f"{key}:build-lock"
        owns_lock = False

        try:
            owns_lock = bool(
                cache.add(
                    lock_key,
                    True,
                    timeout=cls.get_lock_timeout(),
                )
            )
        except Exception:
            logger.exception(
                "ANALYTICS CACHE LOCK FAILED | scope=%s identity=%s section=%s",
                scope,
                identity,
                section,
            )

        if not owns_lock:
            wait_ms = cls.get_lock_wait_ms()
            deadline = time.monotonic() + (wait_ms / 1000)

            while time.monotonic() < deadline:
                time.sleep(0.025)
                try:
                    cached = cls._read(cache, key)
                except Exception:
                    break
                if cached is not _CACHE_MISSING:
                    logger.debug(
                        "ANALYTICS CACHE HIT AFTER WAIT | "
                        "scope=%s identity=%s section=%s",
                        scope,
                        identity,
                        section,
                    )
                    return cached

        try:
            value = builder()

            try:
                cache.set(key, value, timeout=cls.get_timeout())
                logger.info(
                    "ANALYTICS CACHE STORED | "
                    "scope=%s identity=%s section=%s",
                    scope,
                    identity,
                    section,
                )
            except Exception:
                logger.exception(
                    "ANALYTICS CACHE STORE FAILED | "
                    "scope=%s identity=%s section=%s",
                    scope,
                    identity,
                    section,
                )

            return value
        finally:
            if owns_lock:
                try:
                    cache.delete(lock_key)
                except Exception:
                    logger.exception(
                        "ANALYTICS CACHE LOCK RELEASE FAILED | key=%s",
                        lock_key,
                    )


def get_cached_section(*, section: str, days: int, granularity: str):
    """Compatibility wrapper used by the existing system overview builder."""

    from analytics.utils.system_overview_helpers.registry import (
        SECTION_BUILDERS,
        SECTION_DEPENDENCIES,
    )

    builder = SECTION_BUILDERS.get(section)
    if not builder:
        return None

    dependencies = tuple(
        AnalyticsCacheDependency(namespace)
        for namespace in SECTION_DEPENDENCIES[section]
    )

    return AnalyticsCacheService.get_or_build(
        scope="system",
        identity="global",
        section=section,
        dimensions={
            "days": days,
            "granularity": granularity,
        },
        dependencies=dependencies,
        builder=lambda: builder(days=days, granularity=granularity),
    )


def get_cached_system_kpis(*, builder: Callable[[], T]) -> T:
    return AnalyticsCacheService.get_or_build(
        scope="system",
        identity="global",
        section="kpis",
        dimensions={},
        dependencies=(
            AnalyticsCacheDependency(SYSTEM_METRICS),
            AnalyticsCacheDependency(AUTH_METRICS),
            AnalyticsCacheDependency(RETURN_METRICS),
        ),
        builder=builder,
    )


def get_cached_department_section(
    *,
    department,
    section: str,
    days: int,
    granularity: str,
    builder: Callable[[], T],
) -> T:
    identity = str(department.pk)
    dependency = AnalyticsCacheDependency(
        DEPARTMENT_SNAPSHOTS,
        identity=identity,
    )

    return AnalyticsCacheService.get_or_build(
        scope="department",
        identity=identity,
        section=section,
        dimensions={
            "days": days,
            "granularity": granularity,
        },
        dependencies=(dependency,),
        builder=builder,
    )


def get_cached_department_kpis(*, department, builder: Callable[[], T]) -> T:
    identity = str(department.pk)
    dependency = AnalyticsCacheDependency(
        DEPARTMENT_SNAPSHOTS,
        identity=identity,
    )

    return AnalyticsCacheService.get_or_build(
        scope="department",
        identity=identity,
        section="kpis",
        dimensions={},
        dependencies=(dependency,),
        builder=builder,
    )

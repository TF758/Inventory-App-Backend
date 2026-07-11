"""Global generation management for site option-list caches.

Department, Location, and Room mutations rotate one global site-options
version. User-scoped response keys include this version, so all older option
responses become unreachable without Redis key scans or wildcard deletes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings
from django.core.cache import caches
from django.db import transaction

logger = logging.getLogger("arms.scope_cache")


class SiteOptionCacheUnavailable(RuntimeError):
    """Raised when a stable site-options generation cannot be read or written."""


@dataclass(frozen=True, slots=True)
class SiteOptionCacheInvalidation:
    old_generation: str | None
    new_generation: str
    reason: str
    cache_alias: str


class SiteOptionCacheService:
    """Manage the global generation used by all site option endpoints."""

    CACHE_PREFIX = "site-options-cache:v1"
    GENERATION_KEY = f"{CACHE_PREFIX}:generation"
    GENERATION_TIMEOUT: int | None = None

    @classmethod
    def get_cache_alias(cls, cache_alias: str | None = None) -> str:
        return str(
            cache_alias
            or getattr(
                settings,
                "SITE_OPTION_CACHE_ALIAS",
                getattr(settings, "USER_SCOPE_CACHE_ALIAS", "default"),
            )
        )

    @classmethod
    def get_cache(cls, cache_alias: str | None = None):
        alias = cls.get_cache_alias(cache_alias)
        try:
            return caches[alias]
        except Exception as exc:
            raise SiteOptionCacheUnavailable(
                f"Unable to load cache alias {alias!r}."
            ) from exc

    @classmethod
    def get_generation(
        cls,
        *,
        cache_alias: str | None = None,
    ) -> str:
        """Return the global site generation, creating it atomically if absent."""

        alias = cls.get_cache_alias(cache_alias)
        backend = cls.get_cache(alias)

        try:
            existing = backend.get(cls.GENERATION_KEY)
        except Exception as exc:
            logger.exception(
                "SITE OPTION CACHE GENERATION READ FAILED | cache_alias=%s",
                alias,
            )
            raise SiteOptionCacheUnavailable(
                "Unable to read the site-options cache generation."
            ) from exc

        if existing:
            logger.debug(
                "SITE OPTION CACHE GENERATION HIT | generation=%s "
                "cache_alias=%s",
                existing,
                alias,
            )
            return str(existing)

        candidate = uuid4().hex

        try:
            created = backend.add(
                cls.GENERATION_KEY,
                candidate,
                timeout=cls.GENERATION_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "SITE OPTION CACHE GENERATION CREATE FAILED | cache_alias=%s",
                alias,
            )
            raise SiteOptionCacheUnavailable(
                "Unable to create the site-options cache generation."
            ) from exc

        if created:
            logger.info(
                "SITE OPTION CACHE GENERATION CREATED | generation=%s "
                "cache_alias=%s",
                candidate,
                alias,
            )
            return candidate

        # Another worker may have won the atomic add race.
        try:
            winner = backend.get(cls.GENERATION_KEY)
        except Exception as exc:
            logger.exception(
                "SITE OPTION CACHE GENERATION RACE READ FAILED | "
                "cache_alias=%s",
                alias,
            )
            raise SiteOptionCacheUnavailable(
                "Unable to resolve the site-options generation race."
            ) from exc

        if winner:
            logger.info(
                "SITE OPTION CACHE GENERATION RACE RESOLVED | "
                "generation=%s cache_alias=%s",
                winner,
                alias,
            )
            return str(winner)

        try:
            backend.set(
                cls.GENERATION_KEY,
                candidate,
                timeout=cls.GENERATION_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "SITE OPTION CACHE GENERATION FALLBACK FAILED | "
                "cache_alias=%s",
                alias,
            )
            raise SiteOptionCacheUnavailable(
                "Unable to establish the site-options cache generation."
            ) from exc

        logger.warning(
            "SITE OPTION CACHE GENERATION FALLBACK SET | generation=%s "
            "cache_alias=%s",
            candidate,
            alias,
        )
        return candidate

    @classmethod
    def invalidate(
        cls,
        *,
        reason: str,
        cache_alias: str | None = None,
    ) -> SiteOptionCacheInvalidation:
        """Rotate the global site-options generation immediately."""

        reason = str(reason or "manual").strip() or "manual"
        alias = cls.get_cache_alias(cache_alias)
        backend = cls.get_cache(alias)

        try:
            old_generation = backend.get(cls.GENERATION_KEY)
        except Exception:
            old_generation = None
            logger.exception(
                "SITE OPTION CACHE INVALIDATION OLD GENERATION READ FAILED | "
                "reason=%s cache_alias=%s",
                reason,
                alias,
            )

        new_generation = uuid4().hex

        try:
            backend.set(
                cls.GENERATION_KEY,
                new_generation,
                timeout=cls.GENERATION_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "SITE OPTION CACHE INVALIDATION FAILED | reason=%s "
                "cache_alias=%s",
                reason,
                alias,
            )
            raise SiteOptionCacheUnavailable(
                "Unable to rotate the site-options cache generation."
            ) from exc

        logger.info(
            "SITE OPTION CACHE INVALIDATED | old_generation=%s "
            "new_generation=%s reason=%s cache_alias=%s",
            old_generation,
            new_generation,
            reason,
            alias,
        )

        return SiteOptionCacheInvalidation(
            old_generation=(
                str(old_generation)
                if old_generation is not None
                else None
            ),
            new_generation=new_generation,
            reason=reason,
            cache_alias=alias,
        )

    @classmethod
    def invalidate_on_commit(
        cls,
        *,
        reason: str,
        cache_alias: str | None = None,
    ) -> None:
        """Rotate after commit and fail open if Redis is temporarily unavailable."""

        reason = str(reason or "manual").strip() or "manual"
        alias = cls.get_cache_alias(cache_alias)

        def callback() -> None:
            try:
                cls.invalidate(
                    reason=reason,
                    cache_alias=alias,
                )
            except SiteOptionCacheUnavailable:
                # The database mutation is already committed. Log the cache
                # failure without turning a successful write into an HTTP 500.
                logger.exception(
                    "SITE OPTION CACHE ON-COMMIT INVALIDATION FAILED | "
                    "reason=%s cache_alias=%s",
                    reason,
                    alias,
                )

        logger.info(
            "SITE OPTION CACHE INVALIDATION SCHEDULED | reason=%s "
            "cache_alias=%s in_atomic_block=%s",
            reason,
            alias,
            transaction.get_connection().in_atomic_block,
        )

        transaction.on_commit(callback)

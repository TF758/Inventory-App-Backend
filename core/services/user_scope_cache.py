"""Per-user scope-cache generation and invalidation helpers.

Every scoped list-cache key includes a generation token owned by the user's
public ID. Rotating that token invalidates all prior keys for the user without
using Redis wildcard scans. The old response keys expire naturally.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings
from django.core.cache import caches
from django.db import transaction

logger = logging.getLogger("arms.scope_cache")


class UserScopeCacheUnavailable(RuntimeError):
    """Raised when the configured cache backend cannot be used safely."""


@dataclass(frozen=True, slots=True)
class UserScopeCacheInvalidation:
    """Details returned after a user's cache generation is rotated."""

    user_public_id: str
    old_generation: str | None
    new_generation: str
    reason: str
    cache_alias: str


class UserScopeCacheService:
    """Manage scoped-cache generations using user public IDs."""

    CACHE_PREFIX = "user-scope-list-cache:v2"
    GENERATION_KEY_PREFIX = f"{CACHE_PREFIX}:generation"
    GENERATION_TIMEOUT: int | None = None

    @classmethod
    def get_cache_alias(cls, cache_alias: str | None = None) -> str:
        return str(
            cache_alias
            or getattr(settings, "USER_SCOPE_CACHE_ALIAS", "default")
        )

    @classmethod
    def get_cache(cls, cache_alias: str | None = None):
        alias = cls.get_cache_alias(cache_alias)
        try:
            return caches[alias]
        except Exception as exc:  # Invalid alias/configuration.
            raise UserScopeCacheUnavailable(
                f"Unable to load cache alias {alias!r}."
            ) from exc

    @classmethod
    def _normalise_public_id(cls, user_public_id: str) -> str:
        value = str(user_public_id or "").strip()
        if not value:
            raise ValueError("user_public_id is required")
        return value

    @classmethod
    def generation_key(cls, user_public_id: str) -> str:
        user_public_id = cls._normalise_public_id(user_public_id)
        return f"{cls.GENERATION_KEY_PREFIX}:user:{user_public_id}"

    @classmethod
    def get_generation(
        cls,
        user_public_id: str,
        *,
        cache_alias: str | None = None,
    ) -> str:
        """Return the current generation, creating it atomically when absent.

        The method is deliberately strict: if Redis cannot provide a stable
        generation, callers must bypass response caching for that request.
        """

        user_public_id = cls._normalise_public_id(user_public_id)
        alias = cls.get_cache_alias(cache_alias)
        backend = cls.get_cache(alias)
        key = cls.generation_key(user_public_id)

        try:
            existing = backend.get(key)
        except Exception as exc:
            logger.exception(
                "SCOPE CACHE GENERATION READ FAILED | "
                "user_public_id=%s cache_alias=%s",
                user_public_id,
                alias,
            )
            raise UserScopeCacheUnavailable(
                "Unable to read the user's cache generation."
            ) from exc

        if existing:
            logger.debug(
                "SCOPE CACHE GENERATION HIT | user_public_id=%s "
                "generation=%s cache_alias=%s",
                user_public_id,
                existing,
                alias,
            )
            return str(existing)

        candidate = uuid4().hex

        try:
            created = backend.add(
                key,
                candidate,
                timeout=cls.GENERATION_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "SCOPE CACHE GENERATION CREATE FAILED | "
                "user_public_id=%s cache_alias=%s",
                user_public_id,
                alias,
            )
            raise UserScopeCacheUnavailable(
                "Unable to create the user's cache generation."
            ) from exc

        if created:
            logger.info(
                "SCOPE CACHE GENERATION CREATED | user_public_id=%s "
                "generation=%s cache_alias=%s",
                user_public_id,
                candidate,
                alias,
            )
            return candidate

        # A different worker may have won the add() race.
        try:
            winner = backend.get(key)
        except Exception as exc:
            logger.exception(
                "SCOPE CACHE GENERATION RACE READ FAILED | "
                "user_public_id=%s cache_alias=%s",
                user_public_id,
                alias,
            )
            raise UserScopeCacheUnavailable(
                "Unable to resolve the cache-generation race."
            ) from exc

        if winner:
            logger.info(
                "SCOPE CACHE GENERATION RACE RESOLVED | "
                "user_public_id=%s generation=%s cache_alias=%s",
                user_public_id,
                winner,
                alias,
            )
            return str(winner)

        # Defensive fallback for an unusual backend race.
        try:
            backend.set(
                key,
                candidate,
                timeout=cls.GENERATION_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "SCOPE CACHE GENERATION FALLBACK FAILED | "
                "user_public_id=%s cache_alias=%s",
                user_public_id,
                alias,
            )
            raise UserScopeCacheUnavailable(
                "Unable to establish a cache generation."
            ) from exc

        logger.warning(
            "SCOPE CACHE GENERATION FALLBACK SET | user_public_id=%s "
            "generation=%s cache_alias=%s",
            user_public_id,
            candidate,
            alias,
        )
        return candidate

    @classmethod
    def invalidate_user(
        cls,
        user_public_id: str,
        *,
        reason: str = "manual",
        cache_alias: str | None = None,
    ) -> UserScopeCacheInvalidation:
        """Rotate one user's generation using their public ID."""

        user_public_id = cls._normalise_public_id(user_public_id)
        alias = cls.get_cache_alias(cache_alias)
        backend = cls.get_cache(alias)
        key = cls.generation_key(user_public_id)

        try:
            old_generation = backend.get(key)
        except Exception:
            # Reading the old value is useful for logs but is not required to
            # invalidate. Still attempt the authoritative set below.
            old_generation = None
            logger.exception(
                "SCOPE CACHE INVALIDATION OLD GENERATION READ FAILED | "
                "user_public_id=%s cache_alias=%s reason=%s",
                user_public_id,
                alias,
                reason,
            )

        new_generation = uuid4().hex

        try:
            backend.set(
                key,
                new_generation,
                timeout=cls.GENERATION_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "SCOPE CACHE INVALIDATION FAILED | user_public_id=%s "
                "cache_alias=%s reason=%s",
                user_public_id,
                alias,
                reason,
            )
            raise UserScopeCacheUnavailable(
                "Unable to rotate the user's cache generation."
            ) from exc

        logger.info(
            "SCOPE CACHE INVALIDATED | user_public_id=%s "
            "old_generation=%s new_generation=%s reason=%s cache_alias=%s",
            user_public_id,
            old_generation,
            new_generation,
            reason,
            alias,
        )

        return UserScopeCacheInvalidation(
            user_public_id=user_public_id,
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
    def invalidate_existing_user(
        cls,
        user_public_id: str,
        *,
        reason: str = "manual",
        cache_alias: str | None = None,
    ) -> UserScopeCacheInvalidation:
        """Validate a public ID before rotating its generation."""

        from users.models.users import User

        exists = User.objects.filter(public_id=user_public_id).exists()
        if not exists:
            raise User.DoesNotExist(
                f"No user exists with public_id={user_public_id!r}"
            )

        return cls.invalidate_user(
            user_public_id,
            reason=reason,
            cache_alias=cache_alias,
        )

    @classmethod
    def invalidate_user_on_commit(
        cls,
        user_public_id: str,
        *,
        reason: str,
        cache_alias: str | None = None,
    ) -> None:
        """Rotate a generation after commit without breaking the HTTP request.

        A role change is already committed by the time this callback runs. A
        temporary Redis failure must be logged loudly, but must not turn that
        successful database change into a misleading HTTP 500 response.
        """

        user_public_id = cls._normalise_public_id(user_public_id)
        alias = cls.get_cache_alias(cache_alias)

        def callback() -> None:
            try:
                cls.invalidate_user(
                    user_public_id,
                    reason=reason,
                    cache_alias=alias,
                )
            except UserScopeCacheUnavailable:
                logger.exception(
                    "SCOPE CACHE ON-COMMIT INVALIDATION FAILED | "
                    "user_public_id=%s reason=%s cache_alias=%s",
                    user_public_id,
                    reason,
                    alias,
                )

        transaction.on_commit(callback)

        logger.debug(
            "SCOPE CACHE INVALIDATION SCHEDULED | user_public_id=%s "
            "reason=%s cache_alias=%s",
            user_public_id,
            reason,
            alias,
        )

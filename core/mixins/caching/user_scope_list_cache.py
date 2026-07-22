"""DRF mixin for short-lived, user-and-active-role scoped list caching."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.db import connection
from django.utils import timezone
from rest_framework.response import Response

from core.services.user_scope_cache import UserScopeCacheService, UserScopeCacheUnavailable
from sites.services.option_cache import SiteOptionCacheService, SiteOptionCacheUnavailable



logger = logging.getLogger("arms.scope_cache")
_CACHE_MISS = object()


@dataclass(slots=True)
class _DatabaseQueryCounter:
    count: int = 0

    def __call__(self, execute, sql, params, many, context):
        self.count += 1
        return execute(sql, params, many, context)


class UserScopeListCacheMixin:
    """Cache a DRF list response per user, active role, and request shape.

    The key includes the user's public ID, a per-user generation token,
    the global site-options generation, ``active_role_id``, the view
    namespace, and a canonical request digest.

    Redis is an optimisation, not a request dependency. Read/generation
    failures therefore bypass the response cache and execute the normal
    database-backed DRF list path.
    """

    scope_cache_namespace: str | None = None

    # ``None`` means read from USER_SCOPE_CACHE_* settings.
    scope_cache_alias: str | None = None
    scope_cache_timeout: int | None = None
    scope_cache_expiry_marker_grace: int | None = None
    scope_cache_debug_headers: bool | None = None
    scope_cache_count_database_queries: bool | None = None
    scope_cache_log_request_params: bool | None = None

    scope_cache_key_prefix = "user-scope-list-cache:v3"

    def list(self, request, *args, **kwargs):
        if not self.should_use_scope_cache(request):
            logger.info(
                "SCOPE CACHE BYPASS | view=%s method=%s authenticated=%s "
                "namespace=%s reason=cache_not_applicable",
                self.__class__.__name__,
                request.method,
                bool(getattr(request.user, "is_authenticated", False)),
                self.scope_cache_namespace,
            )
            return super().list(request, *args, **kwargs)

        cache_alias = self.get_scope_cache_alias()

        try:
            context = self.build_scope_cache_context(
                request,
                cache_alias=cache_alias,
            )
            backend = caches[cache_alias]
        except (
            UserScopeCacheUnavailable,
            SiteOptionCacheUnavailable,
            InvalidCacheBackendError,
        ):
            # Redis generation failures and invalid cache aliases fail open.
            logger.exception(
                "SCOPE CACHE BYPASS | view=%s user_public_id=%s "
                "namespace=%s cache_alias=%s reason=cache_initialisation_failed",
                self.__class__.__name__,
                getattr(request.user, "public_id", None),
                self.scope_cache_namespace,
                cache_alias,
            )
            return self.run_database_path_with_headers(
                request,
                args,
                kwargs,
                status="BYPASS_CACHE_UNAVAILABLE",
                context=self.build_fallback_context(request),
            )

        cache_key = self.build_scope_cache_key(context)
        marker_key = self.build_scope_cache_marker_key(cache_key)
        key_digest = context["request_digest"]

        try:
            cached_payload = backend.get(cache_key, _CACHE_MISS)
        except Exception:
            logger.exception(
                "SCOPE CACHE READ FAILED | user_public_id=%s active_role_id=%s "
                "namespace=%s request_digest=%s cache_alias=%s; "
                "falling back to database",
                context["user_public_id"],
                context["active_role_id"],
                context["namespace"],
                key_digest,
                cache_alias,
            )
            return self.run_database_path_with_headers(
                request,
                args,
                kwargs,
                status="BYPASS_CACHE_READ_FAILED",
                context=context,
            )

        if self.is_valid_cache_payload(cached_payload):
            ttl_remaining = self.get_payload_ttl_remaining(cached_payload)

            # Do not serve a payload whose own expiry timestamp has elapsed,
            # even if the Redis key survives for a few milliseconds longer.
            if ttl_remaining is None or ttl_remaining > 0:
                age_seconds = self.get_payload_age_seconds(cached_payload)

                logger.info(
                    "SCOPE CACHE HIT | user_public_id=%s active_role_id=%s "
                    "namespace=%s generation=%s site_generation=%s request_digest=%s "
                    "ttl_remaining=%s age_seconds=%s cache_alias=%s site_cache_alias=%s%s",
                    context["user_public_id"],
                    context["active_role_id"],
                    context["namespace"],
                    context["generation"],
                    context["site_generation"],
                    key_digest,
                    ttl_remaining,
                    age_seconds,
                    cache_alias,
                    context["site_cache_alias"],
                    self.get_request_log_suffix(context),
                )

                response = Response(
                    cached_payload["data"],
                    status=cached_payload.get("status", 200),
                )
                self.add_scope_cache_headers(
                    response,
                    status="HIT",
                    context=context,
                    ttl_remaining=ttl_remaining,
                    age_seconds=age_seconds,
                )
                return response

            logger.info(
                "SCOPE CACHE PAYLOAD EXPIRED BY TIMESTAMP | "
                "user_public_id=%s namespace=%s request_digest=%s",
                context["user_public_id"],
                context["namespace"],
                key_digest,
            )
            try:
                backend.delete(cache_key)
            except Exception:
                logger.exception(
                    "SCOPE CACHE STALE PAYLOAD DELETE FAILED | cache_key=%s",
                    cache_key,
                )

        elif cached_payload is not _CACHE_MISS:
            logger.warning(
                "SCOPE CACHE INVALID PAYLOAD | user_public_id=%s "
                "namespace=%s request_digest=%s payload_type=%s",
                context["user_public_id"],
                context["namespace"],
                key_digest,
                type(cached_payload).__name__,
            )
            try:
                backend.delete(cache_key)
            except Exception:
                logger.exception(
                    "SCOPE CACHE INVALID PAYLOAD DELETE FAILED | cache_key=%s",
                    cache_key,
                )

        try:
            previously_created = bool(backend.get(marker_key, False))
        except Exception:
            previously_created = False
            logger.exception(
                "SCOPE CACHE MARKER READ FAILED | user_public_id=%s "
                "namespace=%s request_digest=%s cache_alias=%s",
                context["user_public_id"],
                context["namespace"],
                key_digest,
                cache_alias,
            )

        miss_status = "EXPIRED" if previously_created else "COLD_MISS"

        logger.info(
            "SCOPE CACHE %s | user_public_id=%s active_role_id=%s "
            "namespace=%s generation=%s site_generation=%s request_digest=%s "
            "cache_alias=%s site_cache_alias=%s; executing database-backed list%s",
            miss_status,
            context["user_public_id"],
            context["active_role_id"],
            context["namespace"],
            context["generation"],
            context["site_generation"],
            key_digest,
            cache_alias,
            context["site_cache_alias"],
            self.get_request_log_suffix(context),
        )

        response, query_count, elapsed_ms = self.execute_database_list(
            request,
            *args,
            **kwargs,
        )

        self.log_database_path_complete(
            context,
            response,
            query_count,
            elapsed_ms,
        )

        if not self.should_cache_scope_response(response):
            logger.info(
                "SCOPE CACHE RESPONSE NOT STORED | user_public_id=%s "
                "namespace=%s request_digest=%s status_code=%s",
                context["user_public_id"],
                context["namespace"],
                key_digest,
                response.status_code,
            )
            self.add_scope_cache_headers(
                response,
                status=f"{miss_status}_NOT_STORED",
                context=context,
                ttl_remaining=None,
                age_seconds=None,
                sql_query_count=query_count,
                elapsed_ms=elapsed_ms,
            )
            return response

        created_at = timezone.now()
        timeout = self.get_scope_cache_timeout()
        expires_at = created_at + timedelta(seconds=timeout)
        payload = {
            "data": response.data,
            "status": response.status_code,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        try:
            backend.set(cache_key, payload, timeout=timeout)
        except Exception:
            logger.exception(
                "SCOPE CACHE STORE FAILED | user_public_id=%s "
                "namespace=%s request_digest=%s cache_alias=%s",
                context["user_public_id"],
                context["namespace"],
                key_digest,
                cache_alias,
            )
            self.add_scope_cache_headers(
                response,
                status="STORE_FAILED",
                context=context,
                ttl_remaining=None,
                age_seconds=0,
                sql_query_count=query_count,
                elapsed_ms=elapsed_ms,
            )
            return response

        try:
            backend.set(
                marker_key,
                True,
                timeout=timeout + self.get_scope_cache_marker_grace(),
            )
        except Exception:
            # The response was cached successfully. A marker failure only means
            # a later miss may be labelled COLD_MISS instead of EXPIRED.
            logger.exception(
                "SCOPE CACHE MARKER STORE FAILED | user_public_id=%s "
                "namespace=%s request_digest=%s cache_alias=%s",
                context["user_public_id"],
                context["namespace"],
                key_digest,
                cache_alias,
            )

        logger.info(
            "SCOPE CACHE CREATED | user_public_id=%s active_role_id=%s "
            "namespace=%s generation=%s site_generation=%s request_digest=%s "
            "cache_alias=%s site_cache_alias=%s timeout_seconds=%s expires_at=%s "
            "sql_query_count=%s elapsed_ms=%s",
            context["user_public_id"],
            context["active_role_id"],
            context["namespace"],
            context["generation"],
            context["site_generation"],
            key_digest,
            cache_alias,
            context["site_cache_alias"],
            timeout,
            expires_at.isoformat(),
            query_count,
            elapsed_ms,
        )

        self.add_scope_cache_headers(
            response,
            status="CREATED_AFTER_EXPIRED" if previously_created else "CREATED",
            context=context,
            ttl_remaining=timeout,
            age_seconds=0,
            sql_query_count=query_count,
            elapsed_ms=elapsed_ms,
        )
        return response

    def should_use_scope_cache(self, request) -> bool:
        user = request.user
        return bool(
            request.method == "GET"
            and getattr(user, "is_authenticated", False)
            and getattr(user, "public_id", None)
            and self.get_scope_cache_namespace()
        )

    def should_cache_scope_response(self, response: Response) -> bool:
        return response.status_code == 200 and not getattr(
            response,
            "streaming",
            False,
        )

    def get_scope_cache_namespace(self) -> str:
        namespace = str(self.scope_cache_namespace or "").strip()
        if not namespace:
            raise ValueError(
                f"{self.__class__.__name__} must define scope_cache_namespace"
            )
        return namespace

    def get_scope_cache_alias(self) -> str:
        return str(
            self.scope_cache_alias
            or getattr(settings, "USER_SCOPE_CACHE_ALIAS", "default")
        )

    def get_scope_cache_timeout(self) -> int:
        raw_timeout = (
            self.scope_cache_timeout
            if self.scope_cache_timeout is not None
            else getattr(settings, "USER_SCOPE_CACHE_TIMEOUT", 120)
        )
        timeout = int(raw_timeout)
        if timeout <= 0:
            raise ValueError("USER_SCOPE_CACHE_TIMEOUT must be greater than zero")
        return timeout

    def get_scope_cache_marker_grace(self) -> int:
        raw_grace = (
            self.scope_cache_expiry_marker_grace
            if self.scope_cache_expiry_marker_grace is not None
            else getattr(settings, "USER_SCOPE_CACHE_MARKER_GRACE", 300)
        )
        return max(0, int(raw_grace))

    def should_add_debug_headers(self) -> bool:
        if self.scope_cache_debug_headers is not None:
            return bool(self.scope_cache_debug_headers)
        return bool(
            getattr(
                settings,
                "USER_SCOPE_CACHE_DEBUG_HEADERS",
                getattr(settings, "DEBUG", False),
            )
        )

    def should_count_database_queries(self) -> bool:
        if self.scope_cache_count_database_queries is not None:
            return bool(self.scope_cache_count_database_queries)
        return bool(
            getattr(
                settings,
                "USER_SCOPE_CACHE_COUNT_DB_QUERIES",
                getattr(settings, "DEBUG", False),
            )
        )

    def should_log_request_params(self) -> bool:
        if self.scope_cache_log_request_params is not None:
            return bool(self.scope_cache_log_request_params)
        return bool(
            getattr(
                settings,
                "USER_SCOPE_CACHE_LOG_REQUEST_PARAMS",
                getattr(settings, "DEBUG", False),
            )
        )

    def build_scope_cache_context(
        self,
        request,
        *,
        cache_alias: str,
    ) -> dict[str, Any]:
        user = request.user
        user_public_id = str(user.public_id)
        active_role_id = user.active_role_id or "none"
        generation = UserScopeCacheService.get_generation(
            user_public_id,
            cache_alias=cache_alias,
        )
        site_cache_alias = SiteOptionCacheService.get_cache_alias()
        site_generation = SiteOptionCacheService.get_generation(
            cache_alias=site_cache_alias,
        )
        namespace = self.get_scope_cache_namespace()

        query_params = sorted(
            (str(key), str(value))
            for key in request.query_params.keys()
            for value in request.query_params.getlist(key)
        )

        request_shape = {
            "path": request.path,
            "kwargs": sorted(
                (str(key), str(value))
                for key, value in self.kwargs.items()
            ),
            "query_params": query_params,
            "renderer": getattr(
                getattr(request, "accepted_renderer", None),
                "format",
                None,
            ),
            "version": getattr(request, "version", None),
        }

        request_digest = hashlib.sha256(
            json.dumps(
                request_shape,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()[:24]

        return {
            "user_public_id": user_public_id,
            "active_role_id": active_role_id,
            "generation": generation,
            "site_generation": site_generation,
            "site_cache_alias": site_cache_alias,
            "namespace": namespace,
            "request_digest": request_digest,
            "request_shape": request_shape,
            "cache_alias": cache_alias,
        }

    def build_fallback_context(self, request) -> dict[str, Any]:
        return {
            "user_public_id": str(getattr(request.user, "public_id", "unknown")),
            "active_role_id": getattr(request.user, "active_role_id", None) or "none",
            "generation": "unavailable",
            "site_generation": "unavailable",
            "site_cache_alias": SiteOptionCacheService.get_cache_alias(),
            "namespace": str(self.scope_cache_namespace or "unknown"),
            "request_digest": "unavailable",
            "request_shape": {},
            "cache_alias": self.get_scope_cache_alias(),
        }

    def build_scope_cache_key(self, context: dict[str, Any]) -> str:
        return (
            f"{self.scope_cache_key_prefix}:"
            f"user:{context['user_public_id']}:"
            f"user-generation:{context['generation']}:"
            f"site-generation:{context['site_generation']}:"
            f"active-role:{context['active_role_id']}:"
            f"namespace:{context['namespace']}:"
            f"request:{context['request_digest']}"
        )

    def build_scope_cache_marker_key(self, cache_key: str) -> str:
        return f"{cache_key}:previously-created"

    def is_valid_cache_payload(self, payload: Any) -> bool:
        return isinstance(payload, dict) and "data" in payload

    def parse_payload_datetime(
        self,
        payload: dict[str, Any],
        field: str,
    ) -> datetime | None:
        value = payload.get(field)
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            return parsed
        except (TypeError, ValueError):
            return None

    def get_payload_ttl_remaining(self, payload: dict[str, Any]) -> int | None:
        """Calculate TTL from stored metadata; works with Django RedisCache."""

        expires_at = self.parse_payload_datetime(payload, "expires_at")
        if expires_at is None:
            return None
        return max(0, int((expires_at - timezone.now()).total_seconds()))

    def get_payload_age_seconds(self, payload: dict[str, Any]) -> int | None:
        created_at = self.parse_payload_datetime(payload, "created_at")
        if created_at is None:
            return None
        return max(0, int((timezone.now() - created_at).total_seconds()))

    def execute_database_list(self, request, *args, **kwargs):
        started = time.perf_counter()
        query_counter = _DatabaseQueryCounter()

        if self.should_count_database_queries():
            with connection.execute_wrapper(query_counter):
                response = super().list(request, *args, **kwargs)
        else:
            response = super().list(request, *args, **kwargs)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return response, query_counter.count, elapsed_ms

    def run_database_path_with_headers(
        self,
        request,
        args,
        kwargs,
        *,
        status: str,
        context: dict[str, Any],
    ):
        response, query_count, elapsed_ms = self.execute_database_list(
            request,
            *args,
            **kwargs,
        )
        self.log_database_path_complete(
            context,
            response,
            query_count,
            elapsed_ms,
        )
        self.add_scope_cache_headers(
            response,
            status=status,
            context=context,
            ttl_remaining=None,
            age_seconds=None,
            sql_query_count=query_count,
            elapsed_ms=elapsed_ms,
        )
        return response

    def log_database_path_complete(
        self,
        context: dict[str, Any],
        response: Response,
        query_count: int,
        elapsed_ms: float,
    ) -> None:
        logger.info(
            "SCOPE CACHE DATABASE PATH COMPLETE | user_public_id=%s "
            "active_role_id=%s namespace=%s generation=%s site_generation=%s "
            "request_digest=%s status_code=%s sql_query_count=%s "
            "elapsed_ms=%s cache_alias=%s site_cache_alias=%s",
            context["user_public_id"],
            context["active_role_id"],
            context["namespace"],
            context["generation"],
            context["site_generation"],
            context["request_digest"],
            response.status_code,
            query_count,
            elapsed_ms,
            context.get("cache_alias"),
            context.get("site_cache_alias"),
        )

    def get_request_log_suffix(self, context: dict[str, Any]) -> str:
        if not self.should_log_request_params():
            return ""
        request_shape = context.get("request_shape") or {}
        return f" query_params={request_shape.get('query_params', [])!r}"

    def add_scope_cache_headers(
        self,
        response: Response,
        *,
        status: str,
        context: dict[str, Any],
        ttl_remaining: int | None,
        age_seconds: int | None,
        sql_query_count: int | None = None,
        elapsed_ms: float | None = None,
    ) -> None:
        if not self.should_add_debug_headers():
            return

        response["X-User-Scope-Cache"] = status
        response["X-User-Scope-Cache-User"] = context["user_public_id"]
        response["X-User-Scope-Cache-Active-Role"] = str(
            context["active_role_id"]
        )
        response["X-User-Scope-Cache-Namespace"] = context["namespace"]
        response["X-User-Scope-Cache-Generation"] = str(
            context["generation"]
        )[:12]
        response["X-User-Scope-Cache-Site-Generation"] = str(
            context["site_generation"]
        )[:12]
        response["X-User-Scope-Cache-Request"] = context["request_digest"]

        if ttl_remaining is not None:
            response["X-User-Scope-Cache-TTL"] = str(ttl_remaining)
        if age_seconds is not None:
            response["X-User-Scope-Cache-Age"] = str(age_seconds)
        if sql_query_count is not None:
            response["X-User-Scope-Cache-SQL-Queries"] = str(sql_query_count)
        if elapsed_ms is not None:
            response["X-User-Scope-Cache-Elapsed-MS"] = str(elapsed_ms)

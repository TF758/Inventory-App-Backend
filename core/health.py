"""Unauthenticated container liveness and readiness endpoints."""

from __future__ import annotations

import logging
import uuid

from django.core.cache import caches
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse
from django.views.decorators.http import require_GET


logger = logging.getLogger(__name__)


@require_GET
def liveness(request):
    """Confirm that the Django process can serve HTTP requests."""

    return JsonResponse({"status": "ok", "service": "inventory-api"})


@require_GET
def readiness(request):
    """Confirm that required runtime dependencies are available."""

    checks: dict[str, str] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        logger.exception("readiness_database_check_failed")
        checks["database"] = "unavailable"

    try:
        cache = caches["default"]
        cache_key = f"health:ready:{uuid.uuid4().hex}"
        cache.set(cache_key, "ok", timeout=10)
        cache_value = cache.get(cache_key)
        cache.delete(cache_key)
        if cache_value != "ok":
            raise RuntimeError("Redis cache round-trip failed")
        checks["redis"] = "ok"
    except Exception:
        logger.exception("readiness_redis_check_failed")
        checks["redis"] = "unavailable"

    try:
        executor = MigrationExecutor(connection)
        pending_migrations = executor.migration_plan(
            executor.loader.graph.leaf_nodes()
        )
        checks["migrations"] = (
            "ok" if not pending_migrations else "pending"
        )
    except Exception:
        logger.exception("readiness_migration_check_failed")
        checks["migrations"] = "unavailable"

    ready = all(value == "ok" for value in checks.values())

    return JsonResponse(
        {
            "status": "ok" if ready else "unavailable",
            "checks": checks,
        },
        status=200 if ready else 503,
    )

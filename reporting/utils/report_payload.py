# inventory_metrics/utils/report_payload.py

from django.utils import timezone
from django.conf import settings


def wrap_report_payload(
    *,
    report_type: str,
    data: dict | list,
    schema_version: int | None = None,
    generated_at=None,
    extra_meta: dict | None = None,
) -> dict:
    """
    Wrap a report payload with metadata.

    Args:
        report_type: Logical report identifier (e.g. 'user_summary')
        data: The actual report payload
        schema_version: Optional override (defaults to SNAPSHOT_SCHEMA_VERSION)
        generated_at: Optional override (defaults to now)
        extra_meta: Optional extension hook for future metadata

    Returns:
        dict: { meta: {...}, data: ... }
    """

    meta = {
        "report_type": report_type,
        "generated_at": (generated_at or timezone.now()).isoformat(),
        "schema_version": (
            schema_version
            if schema_version is not None
            else getattr(settings, "SNAPSHOT_SCHEMA_VERSION", 1)
        ),
    }

    if extra_meta:
        meta.update(extra_meta)

    return {
        "meta": meta,
        "data": data,
    }

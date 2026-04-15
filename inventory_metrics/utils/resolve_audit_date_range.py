from datetime import timedelta
from django.utils import timezone

from db_inventory.models.audit import AuditLog

MAX_YEARS = 5

RELATIVE_RANGES = {
    "last_30_days": timedelta(days=30),
    "last_90_days": timedelta(days=90),
    "last_1_year": timedelta(days=365),
    "last_2_years": timedelta(days=365 * 2),
    "last_3_years": timedelta(days=365 * 3),
}


def resolve_audit_date_range(
    *,
    start_date=None,
    end_date=None,
    relative_range=None,
):
    """
    Resolve and sanitize the audit log date range.

    Rules:
    - relative_range overrides explicit dates
    - end_date cannot exceed now
    - start_date cannot precede earliest audit log
    - max window enforced (MAX_YEARS)

    Returns:
        (start_date, end_date)
    """

    now = timezone.now()

    # -------------------------------------------------
    # Relative range override
    # -------------------------------------------------

    if relative_range:

        delta = RELATIVE_RANGES.get(relative_range)

        if not delta:
            raise ValueError("Invalid relative_range value")

        start_date = now - delta
        end_date = now

    # -------------------------------------------------
    # Default end date
    # -------------------------------------------------

    if not end_date:
        end_date = now

    if end_date > now:
        end_date = now

    # -------------------------------------------------
    # Earliest audit log boundary
    # -------------------------------------------------

    earliest = (
        AuditLog.objects
        .order_by("created_at")
        .values_list("created_at", flat=True)
        .first()
    )

    if earliest and start_date and start_date < earliest:
        start_date = earliest

    # -------------------------------------------------
    # Max window guard
    # -------------------------------------------------

    if start_date:

        delta_years = (end_date - start_date).days / 365

        if delta_years > MAX_YEARS:
            raise RuntimeError(
                f"Date range exceeds maximum allowed window ({MAX_YEARS} years)"
            )

    return start_date, end_date

def resolve_report_date_range(params: dict):
    """
    Resolve report date range from either explicit dates or relative_range.

    Returns
    -------
    (start_date, end_date)
    """

    start_date = params.get("start_date")
    end_date = params.get("end_date")
    relative = params.get("relative_range")

    now = timezone.now().date()

    if relative:

        if relative == "last_30_days":
            start_date = now - timedelta(days=30)

        elif relative == "last_90_days":
            start_date = now - timedelta(days=90)

        elif relative == "last_1_year":
            start_date = now - timedelta(days=365)

        elif relative == "last_2_years":
            start_date = now - timedelta(days=730)

        elif relative == "last_3_years":
            start_date = now - timedelta(days=1095)

        end_date = now

    else:
        # If no relative range provided, use explicit dates
        # fallback end_date if missing
        if not end_date:
            end_date = now

    return start_date, end_date
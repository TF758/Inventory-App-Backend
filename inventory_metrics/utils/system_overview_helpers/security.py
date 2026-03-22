from django.db.models import Max, OuterRef, Subquery,  Sum
from inventory_metrics.models.metrics import DailyAuthMetrics, DailySystemMetrics
from inventory_metrics.utils.analytics_helpers import truncate_date
from inventory_metrics.utils.viewset_helpers import get_snapshot_range_start


def build_session_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start( model=DailySystemMetrics, days=days, )

    if not start:
        return []


    base = ( DailySystemMetrics.objects .filter(date__gte=start) .annotate(period=truncate_date("date", granularity)) )

    latest_per_period = ( base .values("period") .annotate(latest_date=Max("date")) )

    snapshot_qs = (
        base
        .filter(
            date=Subquery(
                latest_per_period
                .filter(period=OuterRef("period"))
                .values("latest_date")[:1]
            )
        )
    )

    events_qs = (
        base
        .values("period")
        .annotate(
            revoked_sessions=Sum("revoked_sessions"),
            expired_sessions=Sum("expired_sessions_last_24h"),
        )
    )

    events_by_period = {
        row["period"]: row
        for row in events_qs
    }

    return [
        {
            "date": row.period.isoformat(),
            "active_sessions": row.active_sessions,
            "revoked_sessions": events_by_period[row.period]["revoked_sessions"],
            "expired_sessions": events_by_period[row.period]["expired_sessions"],
        }
        for row in snapshot_qs.order_by("period")
    ]


def build_security_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailySystemMetrics,
        days=days,
    )

    if not start:
        return []

    qs = (
        DailyAuthMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
        .values("period")
        .annotate(
            failed_logins=Sum("failed_logins"),
            lockouts=Sum("lockouts"),
            total_logins=Sum("total_logins"),
        )
        .order_by("period")
    )

    return [
        {
            "date": row["period"].isoformat(),
            "failed_logins": row["failed_logins"],
            "lockouts": row["lockouts"],
            "total_logins": row["total_logins"],
        }
        for row in qs
    ]


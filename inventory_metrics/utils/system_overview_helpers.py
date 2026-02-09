from datetime import timedelta
from django.utils import timezone
from django.db.models import Max, OuterRef, Subquery, DateField
from inventory_metrics.utils.viewset_helpers import get_snapshot_range_start
from inventory_metrics.models.metrics import DailyAuthMetrics, DailySystemMetrics
from inventory_metrics.utils.analytics_helpers import percentage_delta, truncate_date
from django.db.models import Sum





def build_system_kpis():
    today = DailySystemMetrics.objects.order_by("-date").first()
    yesterday = (
        DailySystemMetrics.objects
        .filter(date=today.date - timedelta(days=1))
        .first()
        if today else None
    )

    auth_today = DailyAuthMetrics.objects.filter(date=today.date).first() if today else None
    auth_yesterday = (
        DailyAuthMetrics.objects
        .filter(date=today.date - timedelta(days=1))
        .first()
        if today else None
    )

    def safe_delta(current, previous):
        return percentage_delta(current, previous) if current is not None else None

    return {
        "total_users": {
            "value": today.total_users if today else 0,
            "delta": safe_delta(
                today.total_users if today else None,
                yesterday.total_users if yesterday else None,
            ),
        },
        "active_users": {
            "value": today.active_users_last_7d if today else 0,
            "delta": safe_delta(
                today.active_users_last_7d if today else None,
                yesterday.active_users_last_7d if yesterday else None,
            ),
        },
        "total_equipment": {
            "value": today.total_equipment if today else 0,
            "delta": safe_delta(
                today.total_equipment if today else None,
                yesterday.total_equipment if yesterday else None,
            ),
        },
        "active_sessions": {
            "value": today.active_sessions if today else 0,
            "delta": safe_delta(
                today.active_sessions if today else None,
                yesterday.active_sessions if yesterday else None,
            ),
        },
        "failed_logins": {
            "value": auth_today.failed_logins if auth_today else 0,
            "delta": safe_delta(
                auth_today.failed_logins if auth_today else None,
                auth_yesterday.failed_logins if auth_yesterday else None,
            ),
        },
    }

def build_user_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailySystemMetrics,
        days=days,
    )

    if not start:
        return []

    base = (
        DailySystemMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
    )

    latest_per_period = (
        base
        .values("period")
        .annotate(latest_date=Max("date"))
    )

    qs = (
        base
        .filter(
            date=Subquery(
                latest_per_period
                .filter(period=OuterRef("period"))
                .values("latest_date")[:1]
            )
        )
        .order_by("period")
    )

    return [
        {
            "date": row.period.isoformat(),
            "total_users": row.total_users,
            "active_users": row.active_users_last_7d,
        }
        for row in qs
    ]

def build_session_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailySystemMetrics,
        days=days,
    )

    if not start:
        return []


    base = (
        DailySystemMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
    )

    latest_per_period = (
        base
        .values("period")
        .annotate(latest_date=Max("date"))
    )

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


def build_asset_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailySystemMetrics,
        days=days,
    )

    if not start:
        return []


    base = (
        DailySystemMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
    )

    latest_per_period = (
        base
        .values("period")
        .annotate(latest_date=Max("date"))
    )

    qs = (
        base
        .filter(
            date=Subquery(
                latest_per_period
                .filter(period=OuterRef("period"))
                .values("latest_date")[:1]
            )
        )
        .order_by("period")
    )

    return [
        {
            "date": row.period.isoformat(),
            "equipment_ok": row.equipment_ok,
            "equipment_under_repair": row.equipment_under_repair,
            "equipment_damaged": row.equipment_damaged,
        }
        for row in qs
    ]

def get_system_overview(*, days: int, granularity: str, sections: list[str]):
    charts = {}

    if "users" in sections:
        charts["users"] = build_user_trends(days=days, granularity=granularity)

    if "sessions" in sections:
        charts["sessions"] = build_session_trends(days=days, granularity=granularity)

    if "security" in sections:
        charts["security"] = build_security_trends(days=days, granularity=granularity)

    if "assets" in sections:
        charts["assets"] = build_asset_trends(days=days, granularity=granularity)

    return {
        "kpis": build_system_kpis(),
        "charts": charts,
    }
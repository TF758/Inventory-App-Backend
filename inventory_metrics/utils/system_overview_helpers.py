from datetime import timedelta
from django.utils import timezone
from django.db.models import Max
from inventory_metrics.models.metrics import DailyAuthMetrics, DailySystemMetrics
from inventory_metrics.utils.analytics_helpers import percentage_delta, truncate_date
from django.db.models import Sum





def build_system_kpis():
    today = DailySystemMetrics.objects.order_by("-date").first()
    if not today:
        return {}

    yesterday = DailySystemMetrics.objects.filter(
        date=today.date - timedelta(days=1)
    ).first()

    auth_today = DailyAuthMetrics.objects.filter(date=today.date).first()
    auth_yesterday = DailyAuthMetrics.objects.filter(
        date=today.date - timedelta(days=1)
    ).first()

    return {
        "total_users": {
            "value": today.total_users,
            "delta": percentage_delta(
                today.total_users,
                yesterday.total_users if yesterday else None,
            ),
        },
        "active_users": {
            "value": today.active_users_last_7d,
            "delta": percentage_delta(
                today.active_users_last_7d,
                yesterday.active_users_last_7d if yesterday else None,
            ),
        },
        "total_equipment": {
            "value": today.total_equipment,
            "delta": percentage_delta(
                today.total_equipment,
                yesterday.total_equipment if yesterday else None,
            ),
        },
        "active_sessions": {
            "value": today.active_sessions,
            "delta": percentage_delta(
                today.active_sessions,
                yesterday.active_sessions if yesterday else None,
            ),
        },
        "failed_logins": {
            "value": auth_today.failed_logins if auth_today else 0,
            "delta": percentage_delta(
                auth_today.failed_logins if auth_today else 0,
                auth_yesterday.failed_logins if auth_yesterday else None,
            ),
        },
    }

def build_user_trends(*, days: int, granularity: str = "daily"):
    start_date = timezone.localdate() - timedelta(days=days)

    qs = (
        DailySystemMetrics.objects
        .filter(date__gte=start_date)
        .annotate(bucket=truncate_date("date", granularity))
        .values("bucket")
        .annotate(
            total_users=Max("total_users"),
            active_users=Max("active_users_last_7d"),
        )
        .order_by("bucket")
    )

    return [
        {
            "date": row["bucket"].isoformat(),
            "total_users": row["total_users"],
            "active_users": row["active_users"],
        }
        for row in qs
    ]

def build_session_trends(*, days: int, granularity: str = "daily"):
    start_date = timezone.localdate() - timedelta(days=days)

    qs = (
        DailySystemMetrics.objects
        .filter(date__gte=start_date)
        .annotate(bucket=truncate_date("date", granularity))
        .values("bucket")
        .annotate(
            active_sessions=Max("active_sessions"),
            revoked_sessions=Max("revoked_sessions"),
            expired_sessions=Max("expired_sessions_last_24h"),
        )
        .order_by("bucket")
    )

    return [
        {
            "date": row["bucket"].isoformat(),
            "active_sessions": row["active_sessions"],
            "revoked_sessions": row["revoked_sessions"],
            "expired_sessions": row["expired_sessions"],
        }
        for row in qs
    ]

def build_security_trends(*, days: int, granularity: str = "daily"):
    start_date = timezone.localdate() - timedelta(days=days)

    qs = (
        DailyAuthMetrics.objects
        .filter(date__gte=start_date)
        .annotate(bucket=truncate_date("date", granularity))
        .values("bucket")
        .annotate(
            failed_logins=Sum("failed_logins"),
            lockouts=Sum("lockouts"),
            total_logins=Sum("total_logins"),
        )
        .order_by("bucket")
    )

    return [
        {
            "date": row["bucket"].isoformat(),
            "failed_logins": row["failed_logins"],
            "lockouts": row["lockouts"],
            "total_logins": row["total_logins"],
        }
        for row in qs
    ]

def build_asset_trends(*, days: int, granularity: str = "daily"):
    start_date = timezone.localdate() - timedelta(days=days)

    qs = (
        DailySystemMetrics.objects
        .filter(date__gte=start_date)
        .annotate(bucket=truncate_date("date", granularity))
        .values("bucket")
        .annotate(
            equipment_ok=Max("equipment_ok"),
            equipment_under_repair=Max("equipment_under_repair"),
            equipment_damaged=Max("equipment_damaged"),
        )
        .order_by("bucket")
    )

    return [
        {
            "date": row["bucket"].isoformat(),
            "equipment_ok": row["equipment_ok"],
            "equipment_under_repair": row["equipment_under_repair"],
            "equipment_damaged": row["equipment_damaged"],
        }
        for row in qs
    ]

def get_system_overview(*, days: int = 30) -> dict:
    return {
        "kpis": build_system_kpis(),
        "charts": {
            "users": build_user_trends(days),
            "sessions": build_session_trends(days),
            "security": build_security_trends(days),
            "assets": build_asset_trends(days),
        },
    }


from django.db.models import Max, OuterRef, Subquery
from inventory_metrics.utils.analytics_helpers import truncate_date
from inventory_metrics.models.metrics import DailySystemMetrics
from inventory_metrics.utils.viewset_helpers import get_snapshot_range_start


def build_asset_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailySystemMetrics,
        days=days,
    )

    if not start:
        return []


    base = ( DailySystemMetrics.objects .filter(date__gte=start) .annotate(period=truncate_date("date", granularity)) )

    latest_per_period = ( base .values("period") .annotate(latest_date=Max("date")) )

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

def build_user_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailySystemMetrics,
        days=days,
    )

    if not start:
        return []

    base = ( DailySystemMetrics.objects .filter(date__gte=start) .annotate(period=truncate_date("date", granularity)) )

    latest_per_period = ( base .values("period") .annotate(latest_date=Max("date")) )

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


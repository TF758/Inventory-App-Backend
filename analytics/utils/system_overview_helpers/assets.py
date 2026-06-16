from django.db.models import Max, OuterRef, Subquery

from analytics.models.metrics import DailySystemMetrics
from analytics.utils.analytics_helpers import truncate_date
from analytics.utils.utils.viewset_helpers import get_snapshot_range_start
from analytics.models.snapshots import DailyDepartmentSnapshot


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

def build_department_asset_trends(*, department, days, granularity):
    start = get_snapshot_range_start(
    model=DailyDepartmentSnapshot,
    days=days,
    date_field="snapshot_date",
    filters={"department": department},
)

    if not start:
        return []

    base = (
        DailyDepartmentSnapshot.objects
        .filter(department=department, snapshot_date__gte=start)
        .annotate(period=truncate_date("snapshot_date", granularity))
    )

    latest_per_period = (
        base.values("period")
        .annotate(latest_date=Max("snapshot_date"))
    )

    qs = (
        base.filter(
            snapshot_date=Subquery(
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
    
def build_department_accessory_trends(*, department, days, granularity):
    start = get_snapshot_range_start(
        model=DailyDepartmentSnapshot,
        days=days,
        date_field="snapshot_date",
        filters={"department": department},
    )

    if not start:
        return []

    base = (
        DailyDepartmentSnapshot.objects
        .filter(
            department=department,
            snapshot_date__gte=start,
        )
        .annotate(period=truncate_date("snapshot_date", granularity))
    )

    latest_per_period = (
        base.values("period")
        .annotate(latest_date=Max("snapshot_date"))
    )

    qs = (
        base.filter(
            snapshot_date=Subquery(
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
            "total_accessories": row.total_accessories,
            "total_accessories_quantity": row.total_accessories_quantity,
        }
        for row in qs
    ]

from django.db.models import Max, OuterRef, Subquery

from analytics.models.metrics import DailySystemMetrics
from analytics.utils.analytics_helpers import percentage_delta, truncate_date
from analytics.utils.utils.viewset_helpers import get_snapshot_range_start
from analytics.models.snapshots import DailyDepartmentSnapshot


def build_inventory_value_kpi(current, previous=None):
    return {
        "value": current,
        "delta": percentage_delta(current, previous),
    }

def build_asset_value_trends(*, days: int, granularity: str):
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
        base.values("period")
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
            "equipment_value": row.total_equipment_value,
            "accessory_value": row.total_accessory_value,
            "consumable_value": row.total_consumable_value,
            "total_inventory_value": row.total_inventory_value,
        }
        for row in qs
    ]


def build_department_asset_value_trends(
    *,
    department,
    days,
    granularity,
):
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
        .annotate(
            period=truncate_date(
                "snapshot_date",
                granularity,
            )
        )
    )

    latest_per_period = (
        base.values("period")
        .annotate(
            latest_date=Max("snapshot_date")
        )
    )

    qs = (
        base.filter(
            snapshot_date=Subquery(
                latest_per_period
                .filter(
                    period=OuterRef("period")
                )
                .values("latest_date")[:1]
            )
        )
        .order_by("period")
    )

    return [
        {
            "date": row.period.isoformat(),
            "equipment_value": row.total_equipment_value,
            "consumable_value": row.total_consumable_value,
            "accessory_value": row.total_accessory_value,
            "total_inventory_value": row.total_inventory_value,
        }
        for row in qs
    ]
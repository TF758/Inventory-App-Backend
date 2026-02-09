from db_inventory.models.site import Department
from inventory_metrics.models.snapshots import DailyDepartmentSnapshot
from inventory_metrics.utils.analytics_helpers import percentage_delta, truncate_date
from inventory_metrics.utils.viewset_helpers import get_snapshot_range_start
from datetime import timedelta

from django.db.models import Max, Subquery, OuterRef
from django.utils import timezone

def build_department_kpis(*, department: Department):
    today = (
        DailyDepartmentSnapshot.objects
        .filter(department=department)
        .order_by("-snapshot_date")
        .first()
    )

    yesterday = (
        DailyDepartmentSnapshot.objects
        .filter(
            department=department,
            snapshot_date=today.snapshot_date - timedelta(days=1),
        )
        .first()
        if today else None
    )

    def safe_delta(current, previous):
        return percentage_delta(current, previous) if current is not None else None

    if not today:
        return {}

    return {
        # People
        "total_users": {
            "value": today.total_users,
            "delta": safe_delta(
                today.total_users,
                yesterday.total_users if yesterday else None,
            ),
        },
        "total_admins": {
            "value": today.total_admins,
            "delta": safe_delta(
                today.total_admins,
                yesterday.total_admins if yesterday else None,
            ),
        },

        # Equipment
        "total_equipment": {
            "value": today.total_equipment,
            "delta": safe_delta(
                today.total_equipment,
                yesterday.total_equipment if yesterday else None,
            ),
        },
        "equipment_ok": {
            "value": today.equipment_ok,
            "delta": safe_delta(
                today.equipment_ok,
                yesterday.equipment_ok if yesterday else None,
            ),
        },
        "equipment_under_repair": {
            "value": today.equipment_under_repair,
            "delta": safe_delta(
                today.equipment_under_repair,
                yesterday.equipment_under_repair if yesterday else None,
            ),
        },
        "equipment_damaged": {
            "value": today.equipment_damaged,
            "delta": safe_delta(
                today.equipment_damaged,
                yesterday.equipment_damaged if yesterday else None,
            ),
        },

        # Consumables
        "total_consumables": {
            "value": today.total_consumables,
            "delta": safe_delta(
                today.total_consumables,
                yesterday.total_consumables if yesterday else None,
            ),
        },
        "total_consumables_quantity": {
            "value": today.total_consumables_quantity,
            "delta": safe_delta(
                today.total_consumables_quantity,
                yesterday.total_consumables_quantity if yesterday else None,
            ),
        },
    }

def build_department_consumable_trends(*, department, days, granularity):
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
            "total_consumables": row.total_consumables,
            "total_consumables_quantity": row.total_consumables_quantity,
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

def build_department_user_trends(*, department, days, granularity):
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
            "total_users": row.total_users,
            "total_admins": row.total_admins,
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

def get_department_overview(*, department, days, granularity, sections):
    charts = {}

    if "users" in sections:
        charts["users"] = build_department_user_trends(
            department=department,
            days=days,
            granularity=granularity,
        )

    if "assets" in sections:
        charts["assets"] = build_department_asset_trends(
            department=department,
            days=days,
            granularity=granularity,
        )

    if "consumables" in sections:
        charts["consumables"] = build_department_consumable_trends(
            department=department,
            days=days,
            granularity=granularity,
        )

    if "accessories" in sections:
        charts["accessories"] = build_department_accessory_trends(
            department=department,
            days=days,
            granularity=granularity,
        )

    return {
        "kpis": build_department_kpis(department=department),
        "charts": charts,
    }

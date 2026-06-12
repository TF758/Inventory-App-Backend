from analytics.utils.system_overview_helpers.assets import build_department_accessory_trends, build_department_asset_trends
from analytics.utils.system_overview_helpers.kpis import build_department_kpis
from analytics.utils.system_overview_helpers.returns import build_department_return_flow_trends, build_department_return_state_trends
from analytics.utils.system_overview_helpers.valuation import build_department_asset_value_trends
from sites.models.sites import Department
from datetime import timedelta

from django.db.models import Max, Subquery, OuterRef, Sum
from django.utils import timezone

from analytics.models.snapshots import DailyDepartmentSnapshot
from analytics.utils.analytics_helpers import percentage_delta, truncate_date
from analytics.utils.utils.viewset_helpers import get_snapshot_range_start


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

    if "return_state" in sections:
        charts["return_state"] = build_department_return_state_trends(
            department=department,
            days=days,
            granularity=granularity,
        )

    if "return_flow" in sections:
        charts["return_flow"] = build_department_return_flow_trends(
            department=department,
            days=days,
            granularity=granularity,
        )
    
    if "asset_value" in sections:
        charts["asset_value"] = (
            build_department_asset_value_trends(
                department=department,
                days=days,
                granularity=granularity,
            )
        )
            

    return {
        "kpis": build_department_kpis(department=department),
        "charts": charts,
    }

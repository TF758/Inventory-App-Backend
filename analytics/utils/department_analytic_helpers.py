from django.db.models import Max, OuterRef, Subquery

from analytics.models.snapshots import DailyDepartmentSnapshot
from analytics.utils.analytics_helpers import truncate_date
from analytics.utils.system_overview_helpers.assets import (
    build_department_accessory_trends,
    build_department_asset_trends,
)
from analytics.utils.system_overview_helpers.kpis import build_department_kpis
from analytics.utils.system_overview_helpers.returns import (
    build_department_return_flow_trends,
    build_department_return_state_trends,
)
from analytics.utils.system_overview_helpers.valuation import (
    build_department_asset_value_trends,
)
from analytics.utils.utils.cache import (
    get_cached_department_kpis,
    get_cached_department_section,
)
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


DEPARTMENT_SECTION_BUILDERS = {
    "users": build_department_user_trends,
    "assets": build_department_asset_trends,
    "consumables": build_department_consumable_trends,
    "accessories": build_department_accessory_trends,
    "return_state": build_department_return_state_trends,
    "return_flow": build_department_return_flow_trends,
    "asset_value": build_department_asset_value_trends,
}


def get_department_overview(*, department, days, granularity, sections):
    charts = {}

    # Keep the original response ordering and silently ignore unknown sections.
    for section, builder in DEPARTMENT_SECTION_BUILDERS.items():
        if section not in sections:
            continue

        charts[section] = get_cached_department_section(
            department=department,
            section=section,
            days=days,
            granularity=granularity,
            builder=lambda builder=builder: builder(
                department=department,
                days=days,
                granularity=granularity,
            ),
        )

    return {
        "kpis": get_cached_department_kpis(
            department=department,
            builder=lambda: build_department_kpis(department=department),
        ),
        "charts": charts,
    }

from datetime import timedelta

from analytics.models.metrics import DailyAuthMetrics, DailyReturnMetrics, DailySystemMetrics
from analytics.utils.analytics_helpers import percentage_delta
from analytics.models.snapshots import DailyDepartmentSnapshot
from sites.models.sites import Department



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

    return_today = DailyReturnMetrics.objects.filter(date=today.date).first() if today else None
    return_yesterday = (
        DailyReturnMetrics.objects
        .filter(date=today.date - timedelta(days=1))
        .first()
        if today else None
    )

    def safe_delta(current, previous):
        return percentage_delta(current, previous) if current is not None else None

    if not today:
        return {}

    return {
        # -------------------------
        # Existing KPIs
        # -------------------------
        "total_users": {
            "value": today.total_users,
            "delta": safe_delta(
                today.total_users,
                yesterday.total_users if yesterday else None,
            ),
        },
        "human_users": {
            "value": today.human_users,
            "delta": safe_delta(
                today.human_users,
                yesterday.human_users if yesterday else None,
            ),
        },
        "system_users": {
            "value": today.system_users,
            "delta": safe_delta(
                today.system_users,
                yesterday.system_users if yesterday else None,
            ),
        },
        "total_equipment": {
            "value": today.total_equipment,
            "delta": safe_delta(
                today.total_equipment,
                yesterday.total_equipment if yesterday else None,
            ),
        },
        "active_sessions": {
            "value": today.active_sessions,
            "delta": safe_delta(
                today.active_sessions,
                yesterday.active_sessions if yesterday else None,
            ),
        },

        # -------------------------
        # User activity
        # -------------------------
        "active_users_today": {
            "value": today.active_users_today,
            "delta": safe_delta(
                today.active_users_today,
                yesterday.active_users_today if yesterday else None,
            ),
        },

        # -------------------------
        # Security
        # -------------------------
        "failed_logins": {
            "value": auth_today.failed_logins if auth_today else 0,
            "delta": safe_delta(
                auth_today.failed_logins if auth_today else None,
                auth_yesterday.failed_logins if auth_yesterday else None,
            ),
        },

        # =====================================================
        # 🔥 RETURN KPIs
        # =====================================================

        "total_return_requests": {
            "value": return_today.total_requests if return_today else 0,
            "delta": safe_delta(
                return_today.total_requests if return_today else None,
                return_yesterday.total_requests if return_yesterday else None,
            ),
        },

        "pending_return_requests": {
            "value": return_today.pending_requests if return_today else 0,
            "delta": safe_delta(
                return_today.pending_requests if return_today else None,
                return_yesterday.pending_requests if return_yesterday else None,
            ),
        },

        "requests_created_today": {
            "value": return_today.requests_created_today if return_today else 0,
            "delta": safe_delta(
                return_today.requests_created_today if return_today else None,
                return_yesterday.requests_created_today if return_yesterday else None,
            ),
        },

        "requests_processed_today": {
            "value": return_today.requests_processed_today if return_today else 0,
            "delta": safe_delta(
                return_today.requests_processed_today if return_today else None,
                return_yesterday.requests_processed_today if return_yesterday else None,
            ),
        },

        "avg_return_processing_time": {
            "value": return_today.avg_processing_time_seconds if return_today else 0,
            "delta": safe_delta(
                return_today.avg_processing_time_seconds if return_today else None,
                return_yesterday.avg_processing_time_seconds if return_yesterday else None,
            ),
        },

        "total_inventory_value": {
            "value": today.total_inventory_value,
            "delta": safe_delta(
                today.total_inventory_value,
                yesterday.total_inventory_value if yesterday else None,
            ),
        },
        "equipment_value": {
            "value": today.total_equipment_value,
            "delta": safe_delta(
                today.total_equipment_value,
                yesterday.total_equipment_value if yesterday else None,
            ),
        },
    }


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
        # -------------------------
        # Returns
        # -------------------------
        "total_return_requests": {
            "value": today.total_return_requests,
            "delta": safe_delta(
                today.total_return_requests,
                yesterday.total_return_requests if yesterday else None,
            ),
        },
        "pending_return_requests": {
            "value": today.pending_return_requests,
            "delta": safe_delta(
                today.pending_return_requests,
                yesterday.pending_return_requests if yesterday else None,
            ),
        },
        "returns_created_24h": {
            "value": today.returns_created_last_24h,
            "delta": safe_delta(
                today.returns_created_last_24h,
                yesterday.returns_created_last_24h if yesterday else None,
            ),
        },
        "returns_processed_24h": {
            "value": today.returns_processed_last_24h,
            "delta": safe_delta(
                today.returns_processed_last_24h,
                yesterday.returns_processed_last_24h if yesterday else None,
            ),
        },
        "total_inventory_value": {
            "value": today.total_inventory_value,
            "delta": safe_delta(
                today.total_inventory_value,
                yesterday.total_inventory_value if yesterday else None,
            ),
        },
        "equipment_value": {
            "value": today.total_equipment_value,
            "delta": safe_delta(
                today.total_equipment_value,
                yesterday.total_equipment_value if yesterday else None,
            ),
        },

        "consumable_value": {
            "value": today.total_consumable_value,
            "delta": safe_delta(
                today.total_consumable_value,
                yesterday.total_consumable_value if yesterday else None,
            ),
        },

        "accessory_value": {
            "value": today.total_accessory_value,
            "delta": safe_delta(
                today.total_accessory_value,
                yesterday.total_accessory_value if yesterday else None,
            ),
        },
    }
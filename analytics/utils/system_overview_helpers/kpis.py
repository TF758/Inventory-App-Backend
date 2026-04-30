from datetime import timedelta

from analytics.models.metrics import DailyAuthMetrics, DailyReturnMetrics, DailySystemMetrics
from analytics.utils.analytics_helpers import percentage_delta



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
        "active_users_24h": {
            "value": today.active_users_last_24h,
            "delta": safe_delta(
                today.active_users_last_24h,
                yesterday.active_users_last_24h if yesterday else None,
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

        "returns_created_24h": {
            "value": return_today.requests_created_today if return_today else 0,
            "delta": safe_delta(
                return_today.requests_created_today if return_today else None,
                return_yesterday.requests_created_today if return_yesterday else None,
            ),
        },

        "returns_processed_24h": {
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
    }


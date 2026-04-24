from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count
from sites.models.sites import UserPlacement
from users.models.users import User
from core.models.audit import AuditLog
from django.db.models import Q,  Min, Max
from django.db.models.functions import TruncDate
from core.models.sessions import UserSession
from django.utils import timezone
from datetime import datetime, time

from reporting.utils.resolve_audit_date_range import resolve_audit_date_range

MAX_YEARS = 5
MAX_ROWS = 5_000_000

RELATIVE_RANGES = {
    "last_30_days": timedelta(days=30),
    "last_90_days": timedelta(days=90),
    "last_1_year": timedelta(days=365),
    "last_2_years": timedelta(days=365 * 2),
    "last_3_years": timedelta(days=365 * 3),
}

def build_user_summary_report(
    *,
    user_identifier: str,
    sections: list[str],
    generated_by=None,
) -> dict:
    """
    Build User Summary Report using canonical payload:
    {
        "meta": {},
        "data": {}
    }
    """

    user = (
        User.objects.filter(public_id=user_identifier).first()
        or User.objects.filter(email=user_identifier).first()
    )

    if not user:
        raise ValueError("User not found")

    data = {}

    # -------------------------------------------------
    # Demographics
    # -------------------------------------------------
    if "demographics" in sections:

        current_location = (
            UserPlacement.objects
            .filter(user=user, is_current=True)
            .select_related("room", "room__location")
            .first()
        )

        data["demographics"] = {
            "full_name": user.get_full_name(),
            "email": user.email,
            "job_title": user.job_title,
            "current_location": (
                f"{current_location.room.name} @ "
                f"{current_location.room.location.name}"
                if current_location else None
            ),
            "current_active_role": (
                user.active_role.get_role_display()
                if user.active_role else None
            ),
        }

    # -------------------------------------------------
    # Login Stats
    # -------------------------------------------------
    if "loginStats" in sections:

        sessions = user.sessions.all()
        thirty_days_ago = timezone.now() - timedelta(days=30)

        data["loginStats"] = {
            "active_sessions": sessions.filter(status="active").count(),
            "revoked_sessions": sessions.filter(status="revoked").count(),
            "expired_sessions": sessions.filter(status="expired").count(),
            "login_frequency_last_30_days": sessions.filter(
                last_used_at__gte=thirty_days_ago
            ).count(),
        }

    # -------------------------------------------------
    # Audit Summary
    # -------------------------------------------------
    if "auditSummary" in sections:

        logs = user.audit_logs.all()

        event_counts = (
            logs.values("event_type")
            .annotate(count=Count("id"))
        )

        data["auditSummary"] = {
            "total": logs.count(),
            "events": {
                row["event_type"]: row["count"]
                for row in event_counts
            },
        }

    # -------------------------------------------------
    # Role Summary
    # -------------------------------------------------
    if "roleSummary" in sections:

        roles = user.role_assignments.select_related(
            "department",
            "location",
            "room",
        )

        data["roleSummary"] = [
            {
                "role_name": role.get_role_display(),
                "scope": (
                    role.department.name if role.department else
                    role.location.name if role.location else
                    role.room.name if role.room else
                    "Entire Site"
                ),
                "assigned_date": role.assigned_date,
            }
            for role in roles
        ]

    # -------------------------------------------------
    # Password Events
    # -------------------------------------------------
    if "passwordevents" in sections:

        resets = user.password_reset_events.all()

        data["passwordevents"] = {
            "total_password_reset_events": resets.count(),
            "active_reset_tokens": resets.filter(
                is_active=True
            ).count(),
        }

    return {
        "meta": {
            "report_name": "User Summary Report",
            "generated_at": timezone.now().isoformat(),
            "generated_by": str(generated_by) if generated_by else None,
            "user_identifier": user_identifier,
            "user_public_id": user.public_id,
            "user_email": user.email,
        },
        "data": data,
    }

def generate_user_audit_history_rows(logs):
    """
    Stream audit history rows for large exports.
    Keeps memory usage constant even for millions of rows.
    """

    for log in logs.order_by("created_at").iterator(chunk_size=5000):

        yield [
            log.created_at,
            log.event_type,
            log.description,
            log.target_model,
            log.target_id,
            log.target_name,
            log.department_name,
            log.location_name,
            log.room_name,
            log.ip_address,
            log.user_agent,
        ]
def build_user_audit_history_report(
    *,
    user_identifier: str,
    start_date=None,
    end_date=None,
    relative_range: str | None = None,
    generated_by=None,
) -> dict:
    """
    Build User Audit History Report using canonical payload:

    {
        "meta": {...},
        "data": {...}
    }
    """

    # -------------------------------------------------
    # Locate User
    # -------------------------------------------------

    user = (
        User.objects.filter(public_id=user_identifier).first()
        or User.objects.filter(email=user_identifier).first()
    )

    if not user:
        raise ValueError("User not found")

    # -------------------------------------------------
    # Resolve Date Range
    # -------------------------------------------------

    start_date, end_date = resolve_audit_date_range(
        start_date=start_date,
        end_date=end_date,
        relative_range=relative_range,
    )

    # -------------------------------------------------
    # Base Query
    # -------------------------------------------------

    logs = AuditLog.objects.filter(
        Q(user=user) |
        Q(user_public_id=user.public_id)
    )

    if start_date:
        logs = logs.filter(created_at__gte=start_date)

    if end_date:
        logs = logs.filter(created_at__lte=end_date)

    # -------------------------------------------------
    # Row Count Guard
    # -------------------------------------------------

    total_rows = logs.count()

    if total_rows > MAX_ROWS:
        raise RuntimeError(
            f"Report exceeds maximum allowed rows ({MAX_ROWS}). "
            "Please narrow the date range."
        )

    # -------------------------------------------------
    # Aggregate Stats
    # -------------------------------------------------

    stats_qs = (
        logs.values("event_type")
        .annotate(count=Count("id"))
        .order_by("event_type")
    )

    audit_stats = {
        row["event_type"]: row["count"]
        for row in stats_qs
        if row["count"] > 0
    }

    # -------------------------------------------------
    # History Rows (generator preserved for streaming)
    # -------------------------------------------------

    history_rows = generate_user_audit_history_rows(logs)

    # -------------------------------------------------
    # Return Canonical Payload
    # -------------------------------------------------

    return {
        "meta": {
            "report_name": "User Audit History Report",
            "generated_at": timezone.now().isoformat(),
            "generated_by": (
                generated_by.get_username()
                if generated_by else None
            ),
            "user_public_id": user.public_id,
            "user_email": user.email,
            "user_full_name": user.get_full_name(),
            "start_date": start_date,
            "end_date": end_date,
        },
        "data": {
            "summary": {
                "total_events": total_rows,
                **audit_stats,
            },
            "history_rows": history_rows,
        },
    }

LOGIN_EVENT_TYPES = [
    AuditLog.Events.LOGIN,
    AuditLog.Events.LOGIN_FAILED,
    AuditLog.Events.LOGOUT,
]


from django.db.models import Count, Q
from django.db.models.functions import TruncDate

def build_user_login_history_report(
    *,
    user_identifier: str,
    start_date,
    end_date,
    generated_by=None,
) -> dict:
    """
    Build User Login History Report using canonical payload:

    {
        "meta": {...},
        "data": {...}
    }
    """

    # -------------------------------------------------
    # Normalize Dates
    # -------------------------------------------------

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    start_dt = timezone.make_aware(
        datetime.combine(start_date, time.min)
    )

    end_dt = timezone.make_aware(
        datetime.combine(end_date, time.max)
    )

    # -------------------------------------------------
    # Locate User
    # -------------------------------------------------

    user = (
        User.objects.filter(public_id=user_identifier).first()
        or User.objects.filter(email=user_identifier).first()
    )

    if not user:
        raise ValueError("User not found")

    # -------------------------------------------------
    # Base Queries
    # -------------------------------------------------

    logs = AuditLog.objects.filter(
        Q(user=user) | Q(user_public_id=user.public_id),
        created_at__gte=start_dt,
        created_at__lte=end_dt,
        event_type__in=LOGIN_EVENT_TYPES,
    )

    sessions = UserSession.objects.filter(
        user=user,
        created_at__gte=start_dt,
        created_at__lte=end_dt,
    )

    # -------------------------------------------------
    # Summary Stats
    # -------------------------------------------------

    login_count = logs.filter(
        event_type=AuditLog.Events.LOGIN
    ).count()

    logout_count = logs.filter(
        event_type=AuditLog.Events.LOGOUT
    ).count()

    failed_login_count = logs.filter(
        event_type=AuditLog.Events.LOGIN_FAILED
    ).count()

    total_attempts = login_count + failed_login_count

    login_success_ratio = (
        round((login_count / total_attempts) * 100, 2)
        if total_attempts > 0 else 0
    )

    first_login = (
        logs.order_by("created_at")
        .values_list("created_at", flat=True)
        .first()
    )

    last_login = (
        logs.values_list("created_at", flat=True)
        .first()
    )

    data = {}

    data["summary_stats"] = {
        "total_logins": login_count,
        "total_logouts": logout_count,
        "failed_logins": failed_login_count,
        "login_success_ratio_percent": login_success_ratio,
        "unique_ips": (
            logs.exclude(ip_address__isnull=True)
            .values("ip_address")
            .distinct()
            .count()
        ),
        "unique_devices": (
            logs.exclude(user_agent__isnull=True)
            .values("user_agent")
            .distinct()
            .count()
        ),
        "first_login": first_login,
        "last_login": last_login,
    }

    # -------------------------------------------------
    # Login History
    # -------------------------------------------------

    data["login_history"] = [
        {
            "timestamp": log.created_at,
            "event_type": log.event_type,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "department": log.department_name,
            "location": log.location_name,
            "room": log.room_name,
        }
        for log in logs
    ]

    # -------------------------------------------------
    # Session Stats
    # -------------------------------------------------

    data["session_stats"] = {
        "total_sessions": sessions.count(),
        "active_sessions": sessions.filter(
            status=UserSession.Status.ACTIVE
        ).count(),
        "revoked_sessions": sessions.filter(
            status=UserSession.Status.REVOKED
        ).count(),
        "expired_sessions": sessions.filter(
            status=UserSession.Status.EXPIRED
        ).count(),
    }

    # -------------------------------------------------
    # IP Breakdown
    # -------------------------------------------------

    data["ip_breakdown"] = list(
        logs.values("ip_address")
        .annotate(
            count=Count("id"),
            first_seen=Min("created_at"),
            last_seen=Max("created_at"),
        )
        .order_by("-count")
    )

    # -------------------------------------------------
    # Device Breakdown
    # -------------------------------------------------

    data["device_breakdown"] = list(
        logs.values("user_agent")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # -------------------------------------------------
    # Timeline
    # -------------------------------------------------

    data["login_timeline"] = list(
        logs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    # -------------------------------------------------
    # Return Canonical Payload
    # -------------------------------------------------

    return {
        "meta": {
            "report_name": "User Login History Report",
            "generated_at": timezone.now().isoformat(),
            "generated_by": (
                generated_by.get_username()
                if generated_by else None
            ),
            "user_public_id": user.public_id,
            "user_email": user.email,
            "user_full_name": user.get_full_name(),
            "start_date": start_date,
            "end_date": end_date,
        },
        "data": data,
    }
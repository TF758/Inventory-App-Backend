from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from db_inventory.models.site import UserPlacement
from db_inventory.models.users import User
from db_inventory.models.audit import AuditLog
from django.db.models import Q

from inventory_metrics.utils import resolve_audit_date_range

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
    Build a User Summary Report.

    This service function gathers user-related data and returns a structured
    dictionary that can later be rendered into a report by the report renderer.

    Parameters
    ----------
    user_identifier : str
        The identifier used to locate the user. This can be either:
        - User.public_id
        - User.email

    sections : list[str]
        A list of report sections to include in the output. Only the requested
        sections will be queried and included in the result.

        Allowed values:
            - "demographics"
            - "loginStats"
            - "roleSummary"
            - "auditSummary"
            - "passwordevents"

    generated_by : User | None
        The user who triggered report generation. This is optional and may be
        used for metadata or auditing purposes.
    """

    user = (
        User.objects.filter(public_id=user_identifier).first()
        or User.objects.filter(email=user_identifier).first()
    )

    if not user:
        raise ValueError("User not found")

    data = {}

    # -------------------------------------------------
    # Demographics Section
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
                f"{current_location.room.name} @ {current_location.room.location.name}"
                if current_location else None
            ),
            "current_active_role": (
                user.active_role.get_role_display()
                if user.active_role else None
            ),
        }

    # -------------------------------------------------
    # Login Statistics
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
                e["event_type"]: e["count"]
                for e in event_counts
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
    # Password Event Summary
    # -------------------------------------------------
    if "passwordevents" in sections:

        resets = user.password_reset_events.all()

        data["passwordevents"] = {
            "total_password_reset_events": resets.count(),
            "active_reset_tokens": resets.filter(is_active=True).count(),
        }

    return data

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
    Build a User Audit History Report.

    Returns:
        {
            report_info: {...},
            audit_stats: {...},
            history: [...]
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
        s["event_type"]: s["count"]
        for s in stats_qs
        if s["count"] > 0
    }

    # -------------------------------------------------
    # History Rows
    # -------------------------------------------------

    history_rows = generate_user_audit_history_rows(logs)

    # -------------------------------------------------
    # Report Metadata
    # -------------------------------------------------

    report_info = {
        "generated_by": generated_by.get_username() if generated_by else None,
        "generated_at": timezone.now(),
        "user_public_id": user.public_id,
        "user_email": user.email,
        "user_full_name": user.get_full_name(),
        "start_date": start_date,
        "end_date": end_date,
        "total_events": total_rows,
    }

    # -------------------------------------------------
    # Return Builder Payload
    # -------------------------------------------------

    return {
        "report_info": report_info,
        "audit_stats": audit_stats,
        "history_rows": history_rows,
    }
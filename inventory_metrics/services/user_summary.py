from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from db_inventory.models.site import UserPlacement
from db_inventory.models.users import User

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
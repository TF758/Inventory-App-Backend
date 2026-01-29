from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from db_inventory.models.audit import AuditLog
from db_inventory.models.roles import RoleAssignment
from db_inventory.models.site import UserLocation
from db_inventory.models.users import User



def build_user_summary_report(*, user_identifier: str, sections: list[str]) -> dict:
    user = (
        User.objects.filter(public_id=user_identifier).first()
        or User.objects.filter(email=user_identifier).first()
    )
    if not user:
        raise ValueError("User not found")

    data = {}

    if "demographics" in sections:
        current_location = (
            UserLocation.objects.filter(user=user, is_current=True)
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

    if "loginStats" in sections:
        sessions = user.sessions.all()
        thirty_days_ago = timezone.now() - timedelta(days=30)

        data["loginStats"] = {
            "last_login": user.last_login,
            "active_sessions": sessions.filter(status="active").count(),
            "revoked_sessions": sessions.filter(status="revoked").count(),
            "expired_sessions": sessions.filter(status="expired").count(),
            "login_frequency_last_30_days": sessions.filter(
                last_used_at__gte=thirty_days_ago
            ).count(),
        }

    if "auditSummary" in sections:
        logs = user.audit_logs.all()

        event_counts = (
            logs.values("event_type")
            .annotate(count=Count("id"))
        )

        data["auditSummary"] = {
            "total": logs.count(),
            "events": {e["event_type"]: e["count"] for e in event_counts},
        }

    return data
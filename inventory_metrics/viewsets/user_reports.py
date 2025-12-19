from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from django.db.models import Count

from db_inventory.models import User, UserLocation, RoleAssignment, AuditLog
from inventory_metrics.serializers.user_report import UserSummaryReportSerializer, UserSummaryReportRequestSerializer


class UserSummaryReport(APIView):
    """
    API endpoint to generate a user summary report as JSON.
    """

    def post(self, request):
        serializer = UserSummaryReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_identifier = serializer.validated_data["user"]
        sections = serializer.validated_data["sections"]

        # Fetch the user
        user = (
            User.objects.filter(public_id=user_identifier).first()
            or User.objects.filter(email=user_identifier).first()
        )
        if not user:
            return Response(
                {"detail": f"User '{user_identifier}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch user by public_id or email
        user = (
            User.objects.filter(public_id=user_identifier).first()
            or User.objects.filter(email=user_identifier).first()
        )
        if not user:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        report_data = {}

        # 1️⃣ Demographics & Current Assignments
        if "demographics" in sections:
            current_location = (
                UserLocation.objects.filter(user=user, is_current=True)
                .select_related("room", "room__location")
                .first()
            )

            report_data["demographics"] = {
                "full_name": user.get_full_name(),
                "email": user.email,
                "job_title": user.job_title,
                "current_location": f"{current_location.room.name} @ {current_location.room.location.name}" if current_location else None,
                "current_active_role": f"{user.active_role.get_role_display()}" if user.active_role else None
            }

        # 2️⃣ Login & Session Statistics
        if "loginStats" in sections:
            sessions = user.sessions.all()
            thirty_days_ago = timezone.now() - timedelta(days=30)

            report_data["loginStats"] = {
                "last_login": user.last_login,
                "account_status": {
                    "is_active": user.is_active,
                    "is_locked": getattr(user, "is_locked", False)
                },
                "active_sessions": sessions.filter(status="active").count(),
                "revoked_sessions": sessions.filter(status="revoked").count(),
                "expired_sessions": sessions.filter(status="expired").count(),
                "date_joined": user.date_joined,
                "login_frequency_last_30_days": sessions.filter(
                    last_used_at__gte=thirty_days_ago
                ).count(),
            }

        # 3️⃣ Roles Held by User
        if "roleSummary" in sections:
            roles = user.role_assignments.select_related(
                "department", "location", "room"
            )

            report_data["roleSummary"] = [
                {
                    "role_name": role.get_role_display(),
                    "scope": self.get_role_scope_object(role),
                    "assigned_date": role.assigned_date,
                }
                for role in roles
            ]

        # 4️⃣ Audit Log Summary
        if "auditSummary" in sections:
            audit_logs = user.audit_logs.all()

            event_counts = (
                audit_logs.filter(
                    event_type__in=[
                        AuditLog.Events.MODEL_CREATED,
                        AuditLog.Events.MODEL_UPDATED,
                        AuditLog.Events.MODEL_DELETED,
                    ]
                )
                .values("event_type")
                .annotate(count=Count("id"))
            )

            most_affected_model = (
                audit_logs.values("target_model")
                .annotate(count=Count("id"))
                .order_by("-count")
                .first()
            )

            report_data["auditSummary"] = {
                "total_audit_logs": audit_logs.count(),
                "event_counts": {e["event_type"]: e["count"] for e in event_counts},
                "most_affected_model": most_affected_model["target_model"] if most_affected_model else None,
            }

        # 5️⃣ Password Reset Events
        if "passwordevents" in sections:
            active_resets = user.password_reset_events.filter(is_active=True).count()
            report_data["passwordevents"] = {
                "total_password_reset_events": user.password_reset_events.count(),
                "active_reset_tokens": active_resets
            }

        serializer = UserSummaryReportSerializer(report_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_role_scope_object(self, role: RoleAssignment) -> dict:
        if role.role == "SITE_ADMIN":
            return {"type": "site", "name": "Entire Site"}

        if role.department:
            return {"type": "department", "name": role.department.name}

        if role.location:
            return {"type": "location", "name": role.location.name}

        if role.room:
            return {"type": "room", "name": role.room.name}

        return {"type": "none", "name": None}


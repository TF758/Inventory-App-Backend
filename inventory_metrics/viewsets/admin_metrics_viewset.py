from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from db_inventory.models import *
from datetime import timedelta
from django.db.models import Count, Q
from db_inventory.permissions import ROLE_HIERARCHY
from django.utils import timezone

# provides snapshot data for application

class AdminMetricsOverview(APIView):
    def get(self, request):
        data = {
            "users": User.objects.count(),
            "equipment": Equipment.objects.count(),
            "components": {
                "types": Component.objects.count(),
                "total_quantity": Component.objects.aggregate(total=Sum("quantity"))["total"] or 0
            },
            "consumables": {
                "types": Consumable.objects.count(),
                "total_quantity": Consumable.objects.aggregate(total=Sum("quantity"))["total"] or 0
            },
            "accessories": {
                "types": Accessory.objects.count(),
                "total_quantity": Accessory.objects.aggregate(total=Sum("quantity"))["total"] or 0
            },
            "rooms": Room.objects.count(),
            "locations": Location.objects.count(),
            "departments": Department.objects.count(),
        }

        return Response(data)


class LoginMetricsOverview(APIView):
    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # Status-based
        total_sessions = UserSession.objects.count()
        active_sessions = UserSession.objects.filter(status=UserSession.Status.ACTIVE).count()
        revoked_sessions = UserSession.objects.filter(status=UserSession.Status.REVOKED).count()
        expired_sessions = UserSession.objects.filter(status=UserSession.Status.EXPIRED).count()

        # Time-based session creation = "logins"
        sessions_last_24h = UserSession.objects.filter(created_at__gte=last_24h).count()
        sessions_last_7d = UserSession.objects.filter(created_at__gte=last_7d).count()

        # Unique users active in time windows
        unique_users_last_24h = (
            UserSession.objects.filter(created_at__gte=last_24h)
            .values("user")
            .distinct()
            .count()
        )

        unique_users_last_7d = (
            UserSession.objects.filter(created_at__gte=last_7d)
            .values("user")
            .distinct()
            .count()
        )

        # Users currently logged in (has at least one ACTIVE session)
        active_users_currently = (
            UserSession.objects.filter(status=UserSession.Status.ACTIVE)
            .values("user")
            .distinct()
            .count()
        )

        # Engagement metric
        user_count = User.objects.count() or 1
        average_sessions_per_user = total_sessions / user_count

        
        # Total users in the system
        total_users = User.objects.count() or 1  # avoid division by zero

        # Unique users who had at least one session in the last 7 days
        unique_users_last_7d = (
            UserSession.objects.filter(created_at__gte=last_7d)
            .values("user")
            .distinct()
            .count()
        )

        # Percentage of active users
        percent_active_last_7d = round((unique_users_last_7d / total_users) * 100, 2)

        data = {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "revoked_sessions": revoked_sessions,
            "expired_sessions": expired_sessions,

            "sessions_last_24h": sessions_last_24h,
            "sessions_last_7d": sessions_last_7d,

            "unique_users_last_24h": unique_users_last_24h,
            "unique_users_last_7d": unique_users_last_7d,

            "active_users_currently": active_users_currently,
            "average_sessions_per_user": round(average_sessions_per_user, 2),

            "percent_users_active_last_7d": percent_active_last_7d,  # << new metric
        }

        return Response(data)

class UserMetricsOverview(APIView):
    """
    General User Metrics for Site Admin dashboard
    """

    def get(self, request):
        now = timezone.now()
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        locked_users = User.objects.filter(is_locked=True).count()

        never_logged_in_count = User.objects.exclude(sessions__isnull=False).count()

        new_users_last_7d = User.objects.filter(date_joined__gte=last_7d).count()
        new_users_last_30d = User.objects.filter(date_joined__gte=last_30d).count()

        data = {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "locked_users": locked_users,
            "never_logged_in_users": never_logged_in_count,
            "new_users_last_7d": new_users_last_7d,
            "new_users_last_30d": new_users_last_30d,
        }

        return Response(data)


class SecurityMetricsOverview(APIView):
    """
    Security-related metrics for Site Admin dashboard
    """

    def get(self, request):
        now = timezone.now()
        window_start = now - timedelta(days=7)  # last 7 days

        # 1. Users with multiple active sessions
        users_multiple_active_sessions = (
            UserSession.objects.filter(status=UserSession.Status.ACTIVE)
            .values('user')
            .annotate(active_count=Count('id'))
            .filter(active_count__gt=1)
            .count()
        )

        # 2. Users requiring password change
        users_force_password_change = User.objects.filter(force_password_change=True).count()

        # 3. Locked users
        locked_users = User.objects.filter(is_locked=True).count()

        # 4. Users with revoked sessions
        users_with_revoked_sessions = (
            UserSession.objects.filter(status=UserSession.Status.REVOKED)
            .values('user')
            .distinct()
            .count()
        )

        # 5. Users with expired sessions in the last 7 days
        users_with_recent_expired_sessions = (
            UserSession.objects.filter(
                status=UserSession.Status.EXPIRED,
                expires_at__gte=window_start
            )
            .values('user')
            .distinct()
            .count()
        )

        # 6. System/demo accounts
        system_users_count = User.objects.filter(is_system_user=True).count()

        # 7. Active password reset tokens
        active_password_resets = PasswordResetEvent.objects.filter(is_active=True).count()

        # 8. Recent password reset requests in last 7 days
        recent_password_resets = PasswordResetEvent.objects.filter(
            created_at__gte=window_start
        ).count()

        # 9. Expired password resets in last 7 days
        expired_password_resets_last_7_days = PasswordResetEvent.objects.filter(
            is_active=False,
            expires_at__gte=window_start,
            expires_at__lte=now
        ).count()

        # 10. Users who have never logged in
        never_logged_in_count = User.objects.exclude(sessions__isnull=False).count()

        data = {
            "users_multiple_active_sessions": users_multiple_active_sessions,
            "users_force_password_change": users_force_password_change,
            "locked_users": locked_users,
            "users_with_revoked_sessions": users_with_revoked_sessions,
            "users_with_expired_sessions_last_7_days": users_with_recent_expired_sessions,
            "system_users_count": system_users_count,
            "active_password_resets": active_password_resets,
            "recent_password_resets_last_7_days": recent_password_resets,
            "expired_password_resets_last_7_days": expired_password_resets_last_7_days,
            "never_logged_in_users": never_logged_in_count,
        }

        return Response(data)

class RoleAssignmentMetricsOverview(APIView):
    """
    Role assignment metrics overview.
    Provides total users per role (any assignment) and count of users who currently have
    it as their active role.
    """

    def get(self, request):
        role_assignments_data = []

        for role_name in ROLE_HIERARCHY.keys():
            # Total users with this role anywhere
            total_users_with_role = User.objects.filter(
                role_assignments__role=role_name
            ).distinct().count()

            # Users who currently have this as active role
            total_users_active = User.objects.filter(
                active_role__role=role_name
            ).count()

            role_assignments_data.append({
                "role": role_name,
                "total_users_with_role": total_users_with_role,
                "total_users_active": total_users_active
            })

        # Users without any active role
        users_without_active_role = User.objects.filter(active_role__isnull=True).count()

        return Response({
            "users_without_active_role": users_without_active_role,
            "role_assignments": role_assignments_data
        })
from django.utils import timezone
from users.selectors.users import human_users_queryset
from core.models.audit import AuditLog
from core.models.security import PasswordResetEvent
from core.models.sessions import UserSession



def active_sessions_queryset():
    """returns all active UserSessions"""
    return  UserSession.objects.filter(
        status=UserSession.Status.ACTIVE
    )


def forced_password_change_users_queryset():
    """returns all non system users under password_change"""
    return human_users_queryset().filter(
        force_password_change=True,
    )

def active_sessions_during_period_queryset( start, end, ):

    """Returns active sessions overlapping a time window."""
    return UserSession.objects.filter(
        status=UserSession.Status.ACTIVE,
        created_at__lt=end,
        expires_at__gte=start,
    )

def session_created_within_period_queryset(period):
    """returns all session created within a set period"""
    return UserSession.objects.filter(
        created_at__gte=period
    )

def login_auditlogs_created_within_period_queryset(period):
    """returns all login audiot log event created within a period"""
    return AuditLog.objects.filter(
        event_type=AuditLog.Events.LOGIN,
        created_at__gte=period,
    )

def active_password_reset_queryset():
    """returns all active password resets that have not been used/expired"""
    now = now or timezone.now()
    return PasswordResetEvent.objects.filter(
        is_active=True,
        used_at__isnull=True,
        expires_at__gte=now,
    )

def password_reset_events_queryset( *, created_after=None, created_before=None, admin_initiated=None, ):
    qs = PasswordResetEvent.objects.all()

    if created_after is not None:
        qs = qs.filter(
            created_at__gte=created_after
        )

    if created_before is not None:
        qs = qs.filter(
            created_at__lt=created_before
        )

    if admin_initiated is True:
        qs = qs.filter(
            admin__isnull=False
        )

    elif admin_initiated is False:
        qs = qs.filter(
            admin__isnull=True
        )

    return qs
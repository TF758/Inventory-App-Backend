from datetime import timedelta
from django.utils import timezone
from core.models import AuditLog
from rest_framework.exceptions import AuthenticationFailed


def is_temporarily_locked(user):

    return (
        user.locked_until is not None
        and user.locked_until > timezone.now()
    )


def is_permanently_locked(user):

    return user.is_locked

def reset_failed_logins(user):

    user.failed_login_attempts = 0
    user.last_failed_login_at = None
    user.locked_until = None

    user.save(update_fields=[
        "failed_login_attempts",
        "last_failed_login_at",
        "locked_until",
    ])


def register_failed_login(
    *,
    user,
    policy,
):

    now = timezone.now()

    # -----------------------------------------
    # Rolling window reset
    # -----------------------------------------

    if (
        user.last_failed_login_at
        and now - user.last_failed_login_at >
        timedelta(
            minutes=policy.reset_failed_attempts_after_minutes
        )
    ):
        user.failed_login_attempts = 0

    # -----------------------------------------
    # Increment counter
    # -----------------------------------------

    user.failed_login_attempts += 1
    user.last_failed_login_at = now

    update_fields = [
        "failed_login_attempts",
        "last_failed_login_at",
    ]

    # -----------------------------------------
    # Temporary lock
    # -----------------------------------------

    if (
        policy.enable_account_lockout
        and user.failed_login_attempts >= policy.lockout_attempts
    ):

        user.locked_until = (
            now +
            timedelta(
                minutes=policy.lockout_duration_minutes
            )
        )

        update_fields.append("locked_until")

        AuditLog.objects.create(
            event_type=AuditLog.Events.ACCOUNT_LOCKED,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
            description="Account temporarily locked",
            metadata={
                "lock_type": "temporary",
                "failed_attempts":
                user.failed_login_attempts,
            },
        )

    # -----------------------------------------
    # Permanent escalation
    # -----------------------------------------

    if (
        user.failed_login_attempts >=
        policy.permanent_lock_threshold
    ):

        user.is_locked = True
        user.locked_reason = (
            "Exceeded maximum failed login attempts"
        )

        update_fields.extend([
            "is_locked",
            "locked_reason",
        ])

        AuditLog.objects.create(
            event_type=AuditLog.Events.ACCOUNT_LOCKED,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
            description="Account permanently locked",
            metadata={
                "lock_type": "permanent",
                "failed_attempts":
                user.failed_login_attempts,
            },
        )

    user.save(update_fields=update_fields)


def validate_user_not_locked(user):

    if is_permanently_locked(user):

        raise AuthenticationFailed(
            "Account is locked. Contact administrator."
        )

    if is_temporarily_locked(user):

        raise AuthenticationFailed(
            "Too many failed login attempts. Try again later."
        )


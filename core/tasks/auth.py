from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
import logging
from users.models.users import User
from core.utils.tokens import PasswordResetToken
from core.models.audit import AuditLog
from datetime import timedelta
from core.models.sessions import UserSession


logger = logging.getLogger(__name__)

def retention_delta(*, minutes_setting=None, days_setting=None):
    if minutes_setting and hasattr(settings, minutes_setting):
        return timedelta(minutes=getattr(settings, minutes_setting))
    return timedelta(days=getattr(settings, days_setting))

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
)
def send_password_reset_email(self, email: str):

    # Case-insensitive lookup
    user = User.objects.filter(email__iexact=email).first()

    # IMPORTANT: silently exit if user does not exist
    if not user:
        return

    # Audit only for real users
    AuditLog.objects.create(
        # Actor
        user=user,
        user_public_id=user.public_id,
        user_email=user.email,

        # Event
        event_type=AuditLog.Events.PASSWORD_RESET_REQUESTED,
        description="Password reset requested",
        metadata={"initiated_by_admin": False},

        # Target snapshot (mirror AuditMixin behavior)
        target_model="User",
        target_id=user.public_id,
        target_name=user.email,
    )

    token_service = PasswordResetToken()
    event = token_service.generate_token(user_public_id=user.public_id)
    if not event:
        logger.warning(
            "password_reset_token_generation_skipped_cooldown",
            extra={"user_id": user.pk},
        )
        return
    token = event.token

    reset_link = f"{settings.FRONTEND_URL}/password-reset/confirm?token={token}"

    try:
        send_mail(
            subject="Password Reset Instructions",
            message=(
                "You requested a password reset.\n\n"
                "Your reset link (expires in 10 minutes):\n\n"
                f"{reset_link}\n\n"
                "If you did not request this, you can safely ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "password_reset_email_send_failed",
            extra={
                "user_id": user.pk,
                "user_public_id": str(user.public_id),
            },
        )
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    retry_backoff=True,
)
def admin_reset_user_password(self, *, user_public_id: str, admin_public_id: str):
    user = User.objects.get(public_id=user_public_id)
    admin = User.objects.get(public_id=admin_public_id)

    token_service = PasswordResetToken()
    event = token_service.generate_token(
        user_public_id=user.public_id,
        admin_public_id=admin.public_id,
    )

    if not event:
        logger.warning(
            "admin_password_reset_token_generation_skipped",
            extra={
                "user_id": user.pk,
                "admin_id": admin.pk,
            },
        )
        return


    reset_link = f"{settings.FRONTEND_URL}/password-reset?token={event.token}"

    try:
        send_mail(
            subject="Administrator-Initiated Password Reset",
            message=(
                "An administrator has initiated a password reset for your account.\n\n"
                "This link expires in 10 minutes:\n\n"
                f"{reset_link}\n\n"
                "If you did not expect this, contact support immediately."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "admin_password_reset_email_send_failed",
            extra={
                "user_id": user.pk,
                "admin_id": admin.pk,
            },
        )
        raise

    # only chnage user if email goes through
    user.force_password_change = True
    user.save(update_fields=["force_password_change"])

    AuditLog.objects.create(
        user=admin,
        user_public_id=admin.public_id,
        user_email=admin.email,
        event_type=AuditLog.Events.ADMIN_RESET_PASSWORD,
        description="Admin initiated password reset",
        metadata={
            "initiated_by_admin": True,
            "admin_public_id": admin.public_id,
        },
        target_model="User",
        target_id=user.public_id,
        target_name=user.email,
    )
    # kill all of The user's actve session to force relogin wiht new password
    UserSession.objects.filter(
    user=user,
    status=UserSession.Status.ACTIVE).update(
        status=UserSession.Status.REVOKED)


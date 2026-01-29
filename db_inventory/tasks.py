from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
import logging

from db_inventory.models.users import User
from db_inventory.utils.tokens import PasswordResetToken
from db_inventory.models.audit import AuditLog

logger = logging.getLogger(__name__)

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
        return
    token = event.token

    reset_link = f"{settings.FRONTEND_URL}/password-reset?token={token}"

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
            "Failed to send password reset email for user %s",
            user.public_id,
        )
        raise
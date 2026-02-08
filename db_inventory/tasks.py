from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
import logging
import time
from db_inventory.models.users import User
from db_inventory.utils.tokens import PasswordResetToken
from db_inventory.models.audit import AuditLog
from db_inventory.models.security import Notification, ScheduledTaskRun
from django.utils import timezone
from datetime import timedelta

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

    reset_link = f"{settings.FRONTEND_URL}/password-reset?token={event.token}"

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



@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def auto_read_stale_notifications(self):
    start_ts = time.monotonic()
    now = timezone.now()

    run = ScheduledTaskRun.objects.create(
        task_name="auto_read_stale_notifications",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting auto-read of stale notifications",
    )

    try:
        info_cutoff = now - retention_delta(
            minutes_setting="NOTIF_INFO_AUTO_READ_MINUTES",
            days_setting="NOTIF_INFO_AUTO_READ_DAYS",
        )

        warning_cutoff = now - retention_delta(
            minutes_setting="NOTIF_WARNING_AUTO_READ_MINUTES",
            days_setting="NOTIF_WARNING_AUTO_READ_DAYS",
        )

        info_updated = (
            Notification.objects
            .filter(
                level=Notification.Level.INFO,
                is_read=False,
                is_deleted=False,
                created_at__lt=info_cutoff,
            )
            .update(is_read=True, read_at=now)
        )

        warning_updated = (
            Notification.objects
            .filter(
                level=Notification.Level.WARNING,
                is_read=False,
                is_deleted=False,
                created_at__lt=warning_cutoff,
            )
            .update(is_read=True, read_at=now)
        )

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = (
            f"info_auto_read={info_updated}, "
            f"warning_auto_read={warning_updated}"
        )

        return {
            "info_auto_read": info_updated,
            "warning_auto_read": warning_updated,
        }

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_notifications(self):
    start_ts = time.monotonic()
    now = timezone.now()
    deleted = {}

    run = ScheduledTaskRun.objects.create(
        task_name="cleanup_notifications",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting notification cleanup",
    )

    try:
        # -------------------------------
        # Soft-deleted notifications
        # -------------------------------
        deleted["soft_info"] = (
            Notification.objects
            .filter(
                is_deleted=True,
                level=Notification.Level.INFO,
                deleted_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_INFO_SOFT_DELETE_MINUTES",
                    days_setting="NOTIF_INFO_SOFT_DELETE_DAYS",
                ),
            )
            .delete()[0]
        )

        deleted["soft_warning"] = (
            Notification.objects
            .filter(
                is_deleted=True,
                level=Notification.Level.WARNING,
                deleted_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_WARNING_SOFT_DELETE_MINUTES",
                    days_setting="NOTIF_WARNING_SOFT_DELETE_DAYS",
                ),
            )
            .delete()[0]
        )

        # -------------------------------
        # Read notifications
        # -------------------------------
        deleted["read_info"] = (
            Notification.objects
            .filter(
                is_read=True,
                level=Notification.Level.INFO,
                read_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_INFO_DELETE_MINUTES",
                    days_setting="NOTIF_INFO_DELETE_DAYS",
                ),
            )
            .delete()[0]
        )

        deleted["read_warning"] = (
            Notification.objects
            .filter(
                is_read=True,
                level=Notification.Level.WARNING,
                read_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_WARNING_DELETE_MINUTES",
                    days_setting="NOTIF_WARNING_DELETE_DAYS",
                ),
            )
            .delete()[0]
        )

        deleted["read_critical"] = (
            Notification.objects
            .filter(
                is_read=True,
                level=Notification.Level.CRITICAL,
                read_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_CRITICAL_DELETE_MINUTES",
                    days_setting="NOTIF_CRITICAL_DELETE_DAYS",
                ),
            )
            .delete()[0]
        )

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = ", ".join(
            f"{k}={v}" for k, v in deleted.items()
        )

        return deleted

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_scheduled_task_runs(self):
    now = timezone.now()
    deleted = {}

    # -------------------------------
    # Successful runs
    # -------------------------------
    deleted["success"] = (
        ScheduledTaskRun.objects
        .filter(
            status=ScheduledTaskRun.Status.SUCCESS,
            run_at__lt=now - retention_delta(
                days_setting="TASKRUN_SUCCESS_RETENTION_DAYS",
            ),
        )
        .delete()[0]
    )

    # -------------------------------
    # Skipped runs
    # -------------------------------
    deleted["skipped"] = (
        ScheduledTaskRun.objects
        .filter(
            status=ScheduledTaskRun.Status.SKIPPED,
            run_at__lt=now - retention_delta(
                days_setting="TASKRUN_SKIPPED_RETENTION_DAYS",
            ),
        )
        .delete()[0]
    )

    # -------------------------------
    # Failed runs (keep longest)
    # -------------------------------
    deleted["failed"] = (
        ScheduledTaskRun.objects
        .filter(
            status=ScheduledTaskRun.Status.FAILED,
            run_at__lt=now - retention_delta(
                days_setting="TASKRUN_FAILED_RETENTION_DAYS",
            ),
        )
        .delete()[0]
    )

    return deleted
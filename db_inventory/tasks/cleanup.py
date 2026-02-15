from celery import shared_task
from django.conf import settings
import logging
import time
from db_inventory.models.security import Notification, ScheduledTaskRun, UserSession
from django.utils import timezone
from datetime import timedelta
import time
from datetime import timedelta
from db_inventory.utils.task_helpers import acquire_lock, batched_delete, batched_notification_delete

NOTIFICATION_CLEANUP_LOCK = 842001
TASKRUN_CLEANUP_LOCK = 842002
USERSESSION_CLEANUP_LOCK = 842003

logger = logging.getLogger(__name__)

def retention_delta(*, minutes_setting=None, days_setting=None):
    if minutes_setting and hasattr(settings, minutes_setting):
        return timedelta(minutes=getattr(settings, minutes_setting))
    return timedelta(days=getattr(settings, days_setting))


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
                created_at__lte=info_cutoff,  
            )
            .update(is_read=True, read_at=now)
        )

        warning_updated = (
            Notification.objects
            .filter(
                level=Notification.Level.WARNING,
                is_read=False,
                is_deleted=False,
                created_at__lte=warning_cutoff,  
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


@shared_task(bind=True)
def auto_soft_delete_notifications(self):
    start_ts = time.monotonic()
    now = timezone.now()

    run = ScheduledTaskRun.objects.create(
        task_name="auto_soft_delete_notifications",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting auto soft delete",
    )

    try:
        info_cutoff = now - retention_delta(
            minutes_setting="NOTIF_INFO_DELETE_MINUTES",
            days_setting="NOTIF_INFO_DELETE_DAYS",
        )

        warning_cutoff = now - retention_delta(
            minutes_setting="NOTIF_WARNING_DELETE_MINUTES",
            days_setting="NOTIF_WARNING_DELETE_DAYS",
        )

        updated = {}

        updated["info"] = Notification.objects.filter(
            level=Notification.Level.INFO,
            is_read=True,
            is_deleted=False,
            read_at__lt=info_cutoff,
        ).update(is_deleted=True, deleted_at=now)

        updated["warning"] = Notification.objects.filter(
            level=Notification.Level.WARNING,
            is_read=True,
            is_deleted=False,
            read_at__lt=warning_cutoff,
        ).update(is_deleted=True, deleted_at=now)

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"info={updated['info']}, warning={updated['warning']}"
        return updated

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()

@shared_task(bind=True)
def cleanup_notifications(self):
    # Prevent concurrent cleanups
    if not acquire_lock(NOTIFICATION_CLEANUP_LOCK):
        return {"skipped": "cleanup already running"}

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
        # Soft-deleted notifications ONLY
        # -------------------------------
        deleted["soft_info"] = batched_notification_delete(
            Notification.objects.filter(
                is_deleted=True,
                level=Notification.Level.INFO,
                deleted_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_INFO_SOFT_DELETE_MINUTES",
                    days_setting="NOTIF_INFO_SOFT_DELETE_DAYS",
                ),
            )
        )

        deleted["soft_warning"] = batched_notification_delete(
            Notification.objects.filter(
                is_deleted=True,
                level=Notification.Level.WARNING,
                deleted_at__lt=now - retention_delta(
                    minutes_setting="NOTIF_WARNING_SOFT_DELETE_MINUTES",
                    days_setting="NOTIF_WARNING_SOFT_DELETE_DAYS",
                ),
            )
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
        run.duration_ms = int(
            (time.monotonic() - start_ts) * 1000
        )
        run.save()

@shared_task(bind=True)
def cleanup_scheduled_task_runs(self):
    if not acquire_lock(TASKRUN_CLEANUP_LOCK):
        return {"skipped": "cleanup already running"}

    start_ts = time.monotonic()
    now = timezone.now()
    deleted = {}

    run = ScheduledTaskRun.objects.create(
        task_name="cleanup_scheduled_task_runs",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting scheduled task run cleanup",
    )

    try:
        deleted["success"] = batched_delete(
            ScheduledTaskRun.objects.filter(
                status=ScheduledTaskRun.Status.SUCCESS,
                run_at__lt=now - retention_delta(
                    days_setting="TASKRUN_SUCCESS_RETENTION_DAYS",
                ),
            )
        )

        deleted["skipped"] = batched_delete(
            ScheduledTaskRun.objects.filter(
                status=ScheduledTaskRun.Status.SKIPPED,
                run_at__lt=now - retention_delta(
                    days_setting="TASKRUN_SKIPPED_RETENTION_DAYS",
                ),
            )
        )

        deleted["failed"] = batched_delete(
            ScheduledTaskRun.objects.filter(
                status=ScheduledTaskRun.Status.FAILED,
                run_at__lt=now - retention_delta(
                    days_setting="TASKRUN_FAILED_RETENTION_DAYS",
                ),
            )
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
        run.duration_ms = int(
            (time.monotonic() - start_ts) * 1000
        )
        run.save()

@shared_task(bind=True)
def cleanup_user_sessions(self):
    if not acquire_lock(USERSESSION_CLEANUP_LOCK):
        return {"skipped": "cleanup already running"}

    start_ts = time.monotonic()
    now = timezone.now()
    deleted = {}

    run = ScheduledTaskRun.objects.create(
        task_name="cleanup_user_sessions",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting user session cleanup",
    )

    try:
        deleted["expired"] = batched_delete(
            UserSession.objects.filter(
                status=UserSession.Status.EXPIRED,
                absolute_expires_at__lt=now - retention_delta(
                    days_setting="SESSION_EXPIRED_RETENTION_DAYS",
                ),
            )
        )

        deleted["revoked"] = batched_delete(
            UserSession.objects.filter(
                status=UserSession.Status.REVOKED,
                absolute_expires_at__lt=now - retention_delta(
                    days_setting="SESSION_REVOKED_RETENTION_DAYS",
                ),
            )
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
        run.duration_ms = int(
            (time.monotonic() - start_ts) * 1000
        )
        run.save()

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def expire_user_sessions(self):
    start_ts = time.monotonic()
    now = timezone.now()

    run = ScheduledTaskRun.objects.create(
        task_name="expire_user_sessions",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting user session expiry",
    )

    try:
        expired = (
            UserSession.objects
            .filter(
                status=UserSession.Status.ACTIVE,
                expires_at__lt=now,
            )
            .update(status=UserSession.Status.EXPIRED)
        )

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"expired={expired}"

        return {"expired": expired}

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int(
            (time.monotonic() - start_ts) * 1000
        )
        run.save()
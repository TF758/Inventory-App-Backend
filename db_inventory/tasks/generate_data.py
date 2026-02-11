from celery import shared_task
import time
from db_inventory.models.security import Notification, ScheduledTaskRun, UserSession
from django.utils import timezone
from datetime import timedelta
import time
import uuid
import random
from datetime import timedelta
from django.contrib.auth import get_user_model


@shared_task(bind=True)
def generate_notifications(self):
    start_ts = time.monotonic()
    now = timezone.now()

    run = ScheduledTaskRun.objects.create(
        task_name="generate_notifications",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting notification generation",
    )

    try:
        users = list(
            get_user_model().objects.all()
        )
        if not users:
            run.status = ScheduledTaskRun.Status.SKIPPED
            run.message = "No users found"
            return {"created": 0}

        notifications = []
        for _ in range(20):  # ← rate knob
            notifications.append(
                Notification(
                    recipient=random.choice(users),
                    level=random.choices(
                        [
                            Notification.Level.INFO,
                            Notification.Level.WARNING,
                            Notification.Level.CRITICAL,
                        ],
                        weights=[80, 15, 5],
                    )[0],
                    type=random.choice(
                        list(Notification.NotificationType.values)
                    ),
                    title="Simulated notification",
                    message="Synthetic event for lifecycle testing",
                )
            )

        Notification.objects.bulk_create(notifications)

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"created={len(notifications)}"
        return {"created": len(notifications)}

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
def generate_user_sessions(self):
    start_ts = time.monotonic()
    now = timezone.now()

    run = ScheduledTaskRun.objects.create(
        task_name="generate_user_sessions",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting user session generation",
    )

    try:
        users = list(
            get_user_model().objects.all()
        )
        if not users:
            run.status = ScheduledTaskRun.Status.SKIPPED
            run.message = "No users found"
            return {"created": 0}

        sessions = []
        for _ in range(10):  # ← rate knob
            created_at = now
            sessions.append(
                UserSession(
                    user=random.choice(users),
                    refresh_token_hash=UserSession.hash_token(
                        str(uuid.uuid4())
                    ),
                    status=UserSession.Status.ACTIVE,
                    expires_at=created_at + timedelta(hours=2),
                    absolute_expires_at=created_at + timedelta(days=7),
                )
            )

        UserSession.objects.bulk_create(sessions)

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"created={len(sessions)}"
        return {"created": len(sessions)}

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int(
            (time.monotonic() - start_ts) * 1000
        )
        run.save()


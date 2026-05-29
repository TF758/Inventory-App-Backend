
import logging
import time

from celery import shared_task

from core.models.tasks import ScheduledTaskRun
from agreements.service import AgreementLifecycleService



logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_expired_agreements(self):

    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="sync_expired_agreements",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting agreement expiry sync",
    )

    try:

        expired_count = (
            AgreementLifecycleService
            .sync_expired_agreements()
        )

        run.status = (
            ScheduledTaskRun.Status.SUCCESS
        )

        run.message = (
            f"expired={expired_count}"
        )

        return {
            "expired": expired_count,
        }

    except Exception as exc:

        run.status = (
            ScheduledTaskRun.Status.FAILED
        )

        run.message = str(exc)

        logger.exception(
            "sync_expired_agreements_failed",
            extra={
                "task": (
                    "sync_expired_agreements"
                ),
            },
        )

        raise

    finally:

        run.duration_ms = int(
            (
                time.monotonic()
                - start_ts
            ) * 1000
        )

        run.save()


import logging
import time
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from core.models.tasks import ScheduledTaskRun
from reporting.models.reports import ReportJob
from reporting.services.storage import delete_report

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def delete_old_reports(self):
    start_ts = time.monotonic()
    deleted_jobs = 0
    deleted_files = 0

    run = ScheduledTaskRun.objects.create(
        task_name="delete_old_reports",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting report cleanup",
    )

    try:
        cutoff = (
            timezone.now()
            - timedelta(days=settings.REPORT_RETENTION_DAYS)
        )

        old_jobs = (
            ReportJob.objects
            .filter(finished_at__lt=cutoff)
            .exclude(
                status__in=[
                    ReportJob.Status.PENDING,
                    ReportJob.Status.RUNNING,
                ]
            )
            .only("id", "report_file")
            .iterator(chunk_size=100)
        )

        for job in old_jobs:
            try:
                if delete_report(job.report_file):
                    deleted_files += 1
            except Exception:
                # Keep the database row so a later cleanup run can retry the
                # remote object deletion instead of orphaning the file.
                logger.exception(
                    "report_retention_object_delete_failed",
                    extra={
                        "job_id": job.id,
                        "report_file": job.report_file,
                    },
                )
                continue

            deleted, _ = (
                ReportJob.objects
                .filter(
                    pk=job.pk,
                    finished_at__lt=cutoff,
                )
                .exclude(
                    status__in=[
                        ReportJob.Status.PENDING,
                        ReportJob.Status.RUNNING,
                    ]
                )
                .delete()
            )
            if deleted:
                deleted_jobs += 1

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = (
            f"Deleted {deleted_jobs} report jobs "
            f"and {deleted_files} report files"
        )

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)

        logger.exception(
            "delete_old_reports_failed",
            extra={
                "task": "delete_old_reports",
            },
        )
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()

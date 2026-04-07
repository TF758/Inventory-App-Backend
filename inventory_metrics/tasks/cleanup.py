import time
from datetime import timedelta
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from db_inventory.models.security import ScheduledTaskRun
from inventory_metrics.models.reports import ReportJob
from django.db import transaction



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
        cutoff = timezone.now() - timedelta(days=settings.REPORT_RETENTION_DAYS)

        old_jobs = ReportJob.objects.filter(
            finished_at__lt=cutoff
        ).exclude(
            status__in=[
                ReportJob.Status.PENDING,
                ReportJob.Status.RUNNING,
            ]
        )

        with transaction.atomic():

            old_jobs = (
                ReportJob.objects
                .select_for_update(skip_locked=True)
                .filter(finished_at__lt=cutoff)
                .exclude(
                    status__in=[
                        ReportJob.Status.PENDING,
                        ReportJob.Status.RUNNING,
                    ]
                )
            )

            for job in old_jobs:

                if job.report_file:
                    file_path = Path(settings.REPORTS_DIR) / job.report_file

                    if file_path.exists():
                        file_path.unlink()
                        deleted_files += 1

                job.delete()
                deleted_jobs += 1

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = (
            f"Deleted {deleted_jobs} report jobs "
            f"and {deleted_files} report files"
        )

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()
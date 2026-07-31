import logging
import time
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models.tasks import ScheduledTaskRun
from data_import.utils import delete_import_upload
from reporting.models.reports import ReportJob
from reporting.services.job_dispatch import enqueue_report_job
from reporting.services.job_state import failure_message_for

logger = logging.getLogger(__name__)


def _activity_time(job: ReportJob):
    return job.heartbeat_at or job.started_at or job.created_at


def _is_recoverable(job: ReportJob, *, now) -> bool:
    if job.status == ReportJob.Status.RUNNING:
        cutoff = now - timedelta(seconds=settings.JOB_STALE_AFTER_SECONDS)
        return _activity_time(job) <= cutoff

    if job.status == ReportJob.Status.PENDING:
        cutoff = now - timedelta(
            seconds=settings.JOB_DISPATCH_GRACE_SECONDS
        )
        return _activity_time(job) <= cutoff

    if (
        job.status == ReportJob.Status.DONE
        and job.report_type == ReportJob.ReportType.ASSET_IMPORT
        and job.result_payload is not None
        and not job.report_file
    ):
        cutoff = now - timedelta(
            seconds=settings.JOB_DISPATCH_GRACE_SECONDS
        )
        return (job.finished_at or job.created_at) <= cutoff

    return False


def _cleanup_abandoned_import(job: ReportJob) -> None:
    if job.report_type != ReportJob.ReportType.ASSET_IMPORT:
        return

    stored_file_name = (job.params or {}).get("stored_file_name", "")
    if not stored_file_name:
        return

    try:
        delete_import_upload(stored_file_name)
    except Exception:
        logger.exception(
            "abandoned_import_upload_cleanup_failed",
            extra={"job_id": job.id},
        )


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=settings.MAINTENANCE_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.MAINTENANCE_TASK_TIME_LIMIT,
)
def recover_stale_report_jobs(self):
    start_ts = time.monotonic()
    now = timezone.now()
    stale_cutoff = now - timedelta(seconds=settings.JOB_STALE_AFTER_SECONDS)
    pending_cutoff = now - timedelta(
        seconds=settings.JOB_DISPATCH_GRACE_SECONDS
    )
    recovered = 0
    failed = 0
    dispatch_failed = 0

    run = ScheduledTaskRun.objects.create(
        task_name="recover_stale_report_jobs",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting asynchronous job recovery",
    )

    try:
        candidate_ids = list(
            ReportJob.objects.filter(
                Q(
                    status=ReportJob.Status.RUNNING,
                    heartbeat_at__lte=stale_cutoff,
                )
                | Q(
                    status=ReportJob.Status.RUNNING,
                    heartbeat_at__isnull=True,
                    started_at__lte=stale_cutoff,
                )
                | Q(
                    status=ReportJob.Status.RUNNING,
                    heartbeat_at__isnull=True,
                    started_at__isnull=True,
                    created_at__lte=stale_cutoff,
                )
                | Q(
                    status=ReportJob.Status.PENDING,
                    heartbeat_at__lte=pending_cutoff,
                )
                | Q(
                    status=ReportJob.Status.PENDING,
                    heartbeat_at__isnull=True,
                    created_at__lte=pending_cutoff,
                )
                | Q(
                    status=ReportJob.Status.DONE,
                    report_type=ReportJob.ReportType.ASSET_IMPORT,
                    report_file="",
                    result_payload__isnull=False,
                    finished_at__lte=pending_cutoff,
                )
            )
            .order_by("created_at")
            .values_list("id", flat=True)[:200]
        )

        for job_id in candidate_ids:
            cleanup_job = None

            with transaction.atomic():
                job = (
                    ReportJob.objects
                    .select_for_update()
                    .get(pk=job_id)
                )

                if not _is_recoverable(job, now=now):
                    continue

                if job.attempt_count >= settings.JOB_MAX_ATTEMPTS:
                    job.status = ReportJob.Status.FAILED
                    job.error = failure_message_for(job)
                    job.finished_at = now
                    job.started_at = None
                    job.heartbeat_at = None
                    job.task_id = ""
                    job.save(
                        update_fields=[
                            "status",
                            "error",
                            "finished_at",
                            "started_at",
                            "heartbeat_at",
                            "task_id",
                        ]
                    )
                    failed += 1
                    cleanup_job = job
                else:
                    job.status = ReportJob.Status.PENDING
                    job.started_at = None
                    job.finished_at = None
                    job.heartbeat_at = None
                    job.task_id = ""
                    job.save(
                        update_fields=[
                            "status",
                            "started_at",
                            "finished_at",
                            "heartbeat_at",
                            "task_id",
                        ]
                    )

            if cleanup_job is not None:
                _cleanup_abandoned_import(cleanup_job)
                continue

            if enqueue_report_job(job_id):
                recovered += 1
            else:
                dispatch_failed += 1

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = (
            f"recovered={recovered}, failed={failed}, "
            f"dispatch_failed={dispatch_failed}"
        )
        return {
            "recovered": recovered,
            "failed": failed,
            "dispatch_failed": dispatch_failed,
        }

    except Exception:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = "Asynchronous job recovery failed."
        logger.exception("recover_stale_report_jobs_failed")
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        try:
            run.save()
        except Exception:
            logger.exception("recover_stale_report_jobs_run_log_save_failed")

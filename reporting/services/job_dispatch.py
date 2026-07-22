import logging
import uuid

from django.db import transaction
from django.utils import timezone

from reporting.models.reports import ReportJob

logger = logging.getLogger(__name__)


def task_for_job(job: ReportJob):
    if (
        job.report_type == ReportJob.ReportType.ASSET_IMPORT
        and job.result_payload is None
    ):
        from data_import.tasks import run_asset_import_task

        return run_asset_import_task

    from reporting.tasks.reports import generate_report_task

    return generate_report_task


def enqueue_report_job(job_id: int) -> bool:
    """Reserve a task id and enqueue a job without allowing duplicate sends."""

    task_id = uuid.uuid4().hex
    now = timezone.now()

    with transaction.atomic():
        job = ReportJob.objects.select_for_update().get(pk=job_id)

        if job.status in {
            ReportJob.Status.CANCELLED,
            ReportJob.Status.FAILED,
        }:
            return False

        if job.status == ReportJob.Status.DONE and job.report_file:
            return False

        if job.status == ReportJob.Status.RUNNING:
            return False

        if job.task_id:
            return False

        job.task_id = task_id
        job.heartbeat_at = now
        job.save(update_fields=["task_id", "heartbeat_at"])
        task = task_for_job(job)

    try:
        task.apply_async(args=[job_id], task_id=task_id)
    except Exception:
        ReportJob.objects.filter(
            pk=job_id,
            status=ReportJob.Status.PENDING,
            task_id=task_id,
        ).update(task_id="", heartbeat_at=None)
        logger.exception(
            "report_job_dispatch_failed",
            extra={"job_id": job_id},
        )
        return False

    return True

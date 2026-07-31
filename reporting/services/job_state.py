from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from reporting.models.reports import ReportJob
from reporting.services.job_errors import (
    IMPORT_FAILURE_MESSAGE,
    REPORT_FAILURE_MESSAGE,
)


class JobLeaseLost(RuntimeError):
    pass


@dataclass(frozen=True)
class JobClaim:
    job: ReportJob
    claimed: bool
    reason: str = ""


def failure_message_for(job: ReportJob) -> str:
    if job.report_type == ReportJob.ReportType.ASSET_IMPORT:
        return IMPORT_FAILURE_MESSAGE
    return REPORT_FAILURE_MESSAGE


def _last_activity(job: ReportJob):
    return job.heartbeat_at or job.started_at or job.created_at


def is_job_stale(job: ReportJob, *, now=None) -> bool:
    now = now or timezone.now()
    cutoff = now - timedelta(seconds=settings.JOB_STALE_AFTER_SECONDS)
    return _last_activity(job) <= cutoff


def claim_job(
    job_id: int,
    task_id: str,
    *,
    redelivered: bool = False,
) -> JobClaim:
    """Acquire the database execution lease for a Celery delivery."""

    now = timezone.now()

    with transaction.atomic():
        job = (
            ReportJob.objects
            .select_for_update()
            .select_related("user")
            .get(pk=job_id)
        )

        if job.status in {
            ReportJob.Status.CANCELLED,
            ReportJob.Status.FAILED,
        }:
            return JobClaim(job, False, "terminal")

        if job.status == ReportJob.Status.DONE:
            # Existing asset-import jobs from before P1.3 may have completed the
            # import phase but not yet generated their workbook.
            import_handoff = (
                job.report_type == ReportJob.ReportType.ASSET_IMPORT
                and job.result_payload is not None
                and not job.report_file
            )
            if not import_handoff:
                return JobClaim(job, False, "completed")
            job.status = ReportJob.Status.PENDING

        if job.status == ReportJob.Status.RUNNING:
            if job.task_id == task_id:
                if redelivered:
                    if job.attempt_count >= settings.JOB_MAX_ATTEMPTS:
                        job.status = ReportJob.Status.FAILED
                        job.error = failure_message_for(job)
                        job.finished_at = now
                        job.task_id = ""
                        job.heartbeat_at = None
                        job.save(
                            update_fields=[
                                "status",
                                "error",
                                "finished_at",
                                "task_id",
                                "heartbeat_at",
                            ]
                        )
                        return JobClaim(
                            job,
                            False,
                            "attempts_exhausted",
                        )

                    job.attempt_count += 1
                    update_fields = ["heartbeat_at", "attempt_count"]
                else:
                    update_fields = ["heartbeat_at"]

                job.heartbeat_at = now
                job.save(update_fields=update_fields)
                return JobClaim(job, True, "redelivery")

            if job.task_id and not is_job_stale(job, now=now):
                return JobClaim(job, False, "duplicate")

        if (
            job.status == ReportJob.Status.PENDING
            and job.task_id
            and job.task_id != task_id
        ):
            reservation_cutoff = now - timedelta(
                seconds=settings.JOB_DISPATCH_GRACE_SECONDS
            )
            if job.heartbeat_at and job.heartbeat_at > reservation_cutoff:
                return JobClaim(job, False, "reserved")

        if job.attempt_count >= settings.JOB_MAX_ATTEMPTS:
            job.status = ReportJob.Status.FAILED
            job.error = failure_message_for(job)
            job.finished_at = now
            job.task_id = ""
            job.heartbeat_at = None
            job.save(
                update_fields=[
                    "status",
                    "error",
                    "finished_at",
                    "task_id",
                    "heartbeat_at",
                ]
            )
            return JobClaim(job, False, "attempts_exhausted")

        job.status = ReportJob.Status.RUNNING
        job.started_at = now
        job.finished_at = None
        job.heartbeat_at = now
        job.task_id = task_id
        job.attempt_count += 1
        job.error = ""
        job.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "heartbeat_at",
                "task_id",
                "attempt_count",
                "error",
            ]
        )

        return JobClaim(job, True, "claimed")


def touch_job(job_id: int, task_id: str) -> bool:
    return bool(
        ReportJob.objects.filter(
            pk=job_id,
            status=ReportJob.Status.RUNNING,
            task_id=task_id,
        ).update(heartbeat_at=timezone.now())
    )


def prepare_job_retry(job_id: int, task_id: str) -> bool:
    """Keep the execution lease alive while Celery schedules a retry.

    Celery reuses the current task id for ``self.retry``. Retaining that lease
    prevents the periodic recovery task from treating the retry countdown as
    an orphaned pending job and dispatching a competing delivery.
    """

    return bool(
        ReportJob.objects.filter(
            pk=job_id,
            status=ReportJob.Status.RUNNING,
            task_id=task_id,
        ).filter(
            attempt_count__lt=settings.JOB_MAX_ATTEMPTS,
        ).update(
            attempt_count=F("attempt_count") + 1,
            finished_at=None,
            heartbeat_at=timezone.now(),
        )
    )


def mark_job_failed(
    job_id: int,
    task_id: str,
    *,
    message: str,
    result_payload=None,
) -> bool:
    values = {
        "status": ReportJob.Status.FAILED,
        "error": message,
        "finished_at": timezone.now(),
        "heartbeat_at": None,
        "task_id": "",
    }
    if result_payload is not None:
        values["result_payload"] = result_payload

    return bool(
        ReportJob.objects.filter(
            pk=job_id,
            status=ReportJob.Status.RUNNING,
            task_id=task_id,
        ).update(**values)
    )


def prepare_import_report_handoff(
    job_id: int,
    task_id: str,
    *,
    result_payload,
) -> bool:
    """Persist import results and release the lease for report rendering."""

    return bool(
        ReportJob.objects.filter(
            pk=job_id,
            status=ReportJob.Status.RUNNING,
            task_id=task_id,
        ).update(
            result_payload=result_payload,
            status=ReportJob.Status.PENDING,
            started_at=None,
            finished_at=None,
            heartbeat_at=None,
            task_id="",
            attempt_count=0,
            error="",
        )
    )

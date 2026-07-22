import logging

from celery import shared_task
from django.conf import settings

from core.task_reliability import (
    is_transient_task_error,
    request_is_redelivered,
    request_task_id,
    retry_countdown,
)
from data_import.services.import_builder import build_asset_import
from data_import.utils import delete_import_upload
from reporting.models.reports import ReportJob
from reporting.services.job_dispatch import enqueue_report_job
from reporting.services.job_errors import IMPORT_FAILURE_MESSAGE
from reporting.services.job_state import (
    JobLeaseLost,
    claim_job,
    mark_job_failed,
    prepare_import_report_handoff,
    prepare_job_retry,
)

logger = logging.getLogger(__name__)


def import_failure_payload():
    return {
        "public_error": IMPORT_FAILURE_MESSAGE,
        "summary": {
            "total_rows": 0,
            "imported_rows": 0,
            "skipped_rows": 0,
            "failed_rows": 0,
        },
        "issues": [],
        "fatal_error": IMPORT_FAILURE_MESSAGE,
    }


def cleanup_job_upload(job: ReportJob) -> bool:
    stored_file_name = (job.params or {}).get("stored_file_name", "")
    try:
        return delete_import_upload(stored_file_name)
    except Exception:
        logger.exception(
            "asset_import_upload_cleanup_failed",
            extra={"job_id": job.id},
        )
        return False


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=settings.IMPORT_TASK_MAX_RETRIES,
    soft_time_limit=settings.IMPORT_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.IMPORT_TASK_TIME_LIMIT,
)
def run_asset_import_task(self, report_job_id):
    task_id = request_task_id(self)

    try:
        claim = claim_job(
            report_job_id,
            task_id,
            redelivered=request_is_redelivered(self),
        )
    except ReportJob.DoesNotExist:
        logger.info(
            "asset_import_job_missing",
            extra={"job_id": report_job_id, "task_id": task_id},
        )
        return {"status": "missing"}
    except Exception as exc:
        retries = int(getattr(self.request, "retries", 0) or 0)
        if (
            is_transient_task_error(exc)
            and retries < settings.IMPORT_TASK_MAX_RETRIES
        ):
            raise self.retry(
                exc=exc,
                countdown=retry_countdown(self),
            )
        raise

    job = claim.job

    if not claim.claimed:
        if job.status in {
            ReportJob.Status.CANCELLED,
            ReportJob.Status.FAILED,
        }:
            cleanup_job_upload(job)
        logger.info(
            "asset_import_execution_skipped",
            extra={
                "job_id": job.id,
                "task_id": task_id,
                "reason": claim.reason,
            },
        )
        return {"status": "skipped", "reason": claim.reason}

    if job.report_type != ReportJob.ReportType.ASSET_IMPORT:
        failed = mark_job_failed(
            job.id,
            task_id,
            message=IMPORT_FAILURE_MESSAGE,
            result_payload=import_failure_payload(),
        )
        if failed:
            cleanup_job_upload(job)
        raise RuntimeError("Asset import task received a non-import job.")

    params = job.params or {}

    try:
        # A redelivered handoff must never repeat database imports. If the
        # payload is already present, only ensure report generation is queued.
        if job.result_payload is not None:
            prepared = prepare_import_report_handoff(
                job.id,
                task_id,
                result_payload=job.result_payload,
            )
            if prepared:
                cleanup_job_upload(job)
                enqueue_report_job(job.id)
            return {"status": "report_queued"}

        raw_data = build_asset_import(
            asset_type=params["asset_type"],
            stored_file_name=params["stored_file_name"],
            generated_by=job.user,
            job=job,
        )

        job.refresh_from_db()
        if job.status == ReportJob.Status.CANCELLED:
            cleanup_job_upload(job)
            return {"status": "cancelled"}

        prepared = prepare_import_report_handoff(
            job.id,
            task_id,
            result_payload=raw_data,
        )
        if not prepared:
            logger.info(
                "asset_import_handoff_skipped_after_lease_change",
                extra={"job_id": job.id, "task_id": task_id},
            )
            return {"status": "lease_lost"}

        cleanup_job_upload(job)
        enqueue_report_job(job.id)

        logger.info(
            "asset_import_report_handoff_queued",
            extra={"job_id": job.id, "task_id": task_id},
        )
        return {"status": "report_queued"}

    except JobLeaseLost:
        logger.warning(
            "asset_import_execution_lease_lost",
            extra={"job_id": job.id, "task_id": task_id},
        )
        return {"status": "lease_lost"}

    except ValueError:
        logger.warning(
            "asset_import_validation_failed",
            extra={"job_id": job.id, "user_id": job.user_id},
            exc_info=True,
        )
        failed = mark_job_failed(
            job.id,
            task_id,
            message=IMPORT_FAILURE_MESSAGE,
            result_payload=import_failure_payload(),
        )
        if failed:
            cleanup_job_upload(job)
        return {"status": "failed"}

    except Exception as exc:
        logger.exception(
            "asset_import_task_failed",
            extra={
                "job_id": job.id,
                "user_id": job.user_id,
                "task_id": task_id,
            },
        )

        retries = int(getattr(self.request, "retries", 0) or 0)
        if (
            is_transient_task_error(exc)
            and retries < settings.IMPORT_TASK_MAX_RETRIES
        ):
            try:
                lease_owned = prepare_job_retry(job.id, task_id)
            except Exception:
                # The retry delivery uses the same Celery task id. If the
                # database is temporarily unavailable, retrying is still safe:
                # claim_job will either resume the existing lease or skip the
                # delivery after another owner has taken over.
                lease_owned = True
                logger.exception(
                    "asset_import_retry_lease_refresh_failed",
                    extra={"job_id": job.id, "task_id": task_id},
                )

            if lease_owned:
                raise self.retry(
                    exc=exc,
                    countdown=retry_countdown(self),
                )

        failed = mark_job_failed(
            job.id,
            task_id,
            message=IMPORT_FAILURE_MESSAGE,
            result_payload=import_failure_payload(),
        )
        if failed:
            cleanup_job_upload(job)
        raise

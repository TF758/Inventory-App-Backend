
from celery import shared_task
from data_import.services.import_builder import build_asset_import
from django.utils import timezone
from reporting.tasks.reports import generate_report_task
from reporting.models.reports import ReportJob
import logging
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)



@shared_task(bind=True)
def run_asset_import_task(self, report_job_id):
    job = ReportJob.objects.select_related("user").get(id=report_job_id)

    job.status = ReportJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    params = job.params

    try:
        raw_data = build_asset_import(
            asset_type=params["asset_type"],
            stored_file_name=params["stored_file_name"],
            generated_by=job.user,
            job=job,
        )

        job.refresh_from_db()

        if job.status != ReportJob.Status.CANCELLED:
            job.result_payload = raw_data
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()
            job.error = ""
            job.save(update_fields=["result_payload", "status", "finished_at", "error"])

            # DEBUG: downstream task trigger
            logger.debug(
                "asset_import_triggered_report_generation",
                extra={"job_id": job.id},
            )

            generate_report_task.delay(job.id)
            if default_storage.exists(params["stored_file_name"]):
                default_storage.delete(params["stored_file_name"])

        else:
            # Optional visibility into cancellation
            logger.info(
                "asset_import_cancelled",
                extra={
                    "job_id": job.id,
                    "user_id": job.user_id,
                },
            )

    except ValueError as exc:
        # Controlled / validation failure
        logger.warning(
            "asset_import_validation_failed",
            extra={
                "job_id": job.id,
                "user_id": job.user_id,
            },
        )

        job.status = ReportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error = str(exc)
        job.result_payload = {
            "summary": {
                "total_rows": 0,
                "imported_rows": 0,
                "skipped_rows": 0,
                "failed_rows": 0,
            },
            "issues": [],
            "fatal_error": str(exc),
        }
        job.save(update_fields=["status", "finished_at", "error", "result_payload"])

    except Exception as exc:
        # Unexpected failure
        logger.exception(
            "asset_import_task_failed",
            extra={
                "job_id": job.id,
                "user_id": job.user_id,
            },
        )

        job.status = ReportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error = f"Unexpected import error: {exc}"
        job.result_payload = {
            "summary": {
                "total_rows": 0,
                "imported_rows": 0,
                "skipped_rows": 0,
                "failed_rows": 0,
            },
            "issues": [],
            "fatal_error": "Unexpected import error.",
        }
        job.save(update_fields=["status", "finished_at", "error", "result_payload"])

        raise
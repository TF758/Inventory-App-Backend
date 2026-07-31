import io
import logging
import time
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import is_aware

from core.mixins import NotificationMixin
from core.models.tasks import ScheduledTaskRun
from core.task_reliability import (
    is_transient_task_error,
    request_is_redelivered,
    request_task_id,
    retry_countdown,
)
from reporting.models.reports import ReportJob
from reporting.report_registry import REPORT_DEFINITIONS
from reporting.services.job_errors import REPORT_FAILURE_MESSAGE
from reporting.services.job_state import (
    JobLeaseLost,
    claim_job,
    mark_job_failed,
    prepare_job_retry,
    touch_job,
)
from reporting.services.storage import delete_report, save_report
from reporting.utils.report_payload import wrap_report_payload
from reporting.utils.excel_renderer import (
    render_workbook,
    render_workbook_streaming,
)

logger = logging.getLogger(__name__)


def normalize_datetimes(obj):
    """Recursively convert timezone-aware datetimes for openpyxl."""
    if isinstance(obj, dict):
        return {key: normalize_datetimes(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [normalize_datetimes(value) for value in obj]
    if isinstance(obj, datetime) and is_aware(obj):
        return obj.replace(tzinfo=None)
    return obj


def require_job_lease(job_id: int, task_id: str) -> None:
    if not touch_job(job_id, task_id):
        raise JobLeaseLost(
            "Report execution lease is no longer owned by this task."
        )


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=settings.REPORT_TASK_MAX_RETRIES,
    soft_time_limit=settings.REPORT_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.REPORT_TASK_TIME_LIMIT,
)
def generate_report_task(self, report_job_id: int):
    start_ts = time.monotonic()
    task_id = request_task_id(self)
    notifier = NotificationMixin()
    job = None
    stored_report_name = ""
    run = None

    try:
        run = ScheduledTaskRun.objects.create(
            task_name="generate_report_task",
            status=ScheduledTaskRun.Status.STARTED,
        )
        try:
            claim = claim_job(
                report_job_id,
                task_id,
                redelivered=request_is_redelivered(self),
            )
        except ReportJob.DoesNotExist:
            run.status = ScheduledTaskRun.Status.SKIPPED
            run.message = "Report job no longer exists."
            return {"status": "missing"}

        job = claim.job
        if not claim.claimed:
            run.status = ScheduledTaskRun.Status.SKIPPED
            run.message = f"Report execution skipped: {claim.reason}."
            return {"status": "skipped", "reason": claim.reason}

        definition = REPORT_DEFINITIONS.get(job.report_type)
        if not definition:
            raise RuntimeError(f"Unknown report type: {job.report_type}")

        builder = definition["builder"]
        renderer = definition["renderer"]
        builder_params = definition["param_map"](job.params, job.user)

        if job.report_type == ReportJob.ReportType.ASSET_IMPORT:
            payload = job.result_payload
            if not (
                isinstance(payload, dict)
                and "meta" in payload
                and "data" in payload
            ):
                payload = wrap_report_payload(
                    report_type=job.report_type,
                    data=payload or {},
                    extra_meta={
                        "generated_by": job.user.get_username(),
                        "asset_type": job.params.get("asset_type"),
                        "original_file_name": job.params.get(
                            "original_file_name",
                            "",
                        ),
                    },
                )
        else:
            payload = builder(**builder_params)

        require_job_lease(job.id, task_id)
        payload = normalize_datetimes(payload)

        if payload is None:
            raise RuntimeError("Report payload is empty")
        if not isinstance(payload, dict):
            raise RuntimeError("Report payload must be a dict")
        if not isinstance(payload.get("meta"), dict):
            raise RuntimeError("Report payload missing a valid 'meta' object")
        if not isinstance(payload.get("data"), dict):
            raise RuntimeError("Report payload missing a valid 'data' object")

        payload["meta"].setdefault("report_type", job.report_type)
        payload["meta"].setdefault("generated_by", job.user.get_username())
        payload["meta"].setdefault("schema_version", 1)

        workbook_spec = renderer(payload)
        require_job_lease(job.id, task_id)

        if definition.get("streaming", False):
            workbook = render_workbook_streaming(workbook_spec)
        else:
            workbook = render_workbook(workbook_spec)

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        require_job_lease(job.id, task_id)

        filename = settings.REPORT_FILENAME_TEMPLATE.format(
            report_type=job.report_type,
            public_id=job.public_id,
        )
        # Store each execution under its own key. A stale worker can then
        # clean up only the object it created without deleting the successful
        # output produced by a replacement task. The basename remains the
        # user-facing download filename.
        stored_report_name = save_report(
            f"{job.public_id}/{task_id}/{filename}.xlsx",
            buffer.getvalue(),
        )

        with transaction.atomic():
            locked_job = (
                ReportJob.objects
                .select_for_update()
                .select_related("user")
                .get(pk=job.pk)
            )

            if locked_job.status == ReportJob.Status.CANCELLED:
                raise JobLeaseLost("Report was cancelled before completion.")

            if (
                locked_job.status != ReportJob.Status.RUNNING
                or locked_job.task_id != task_id
            ):
                raise JobLeaseLost(
                    "Report execution lease changed before completion."
                )

            locked_job.status = ReportJob.Status.DONE
            locked_job.finished_at = timezone.now()
            locked_job.report_file = stored_report_name
            locked_job.error = ""
            locked_job.heartbeat_at = None
            locked_job.task_id = ""
            locked_job.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "report_file",
                    "error",
                    "heartbeat_at",
                    "task_id",
                ]
            )

            if not locked_job.notification_sent:
                notifier.notify(
                    recipient=locked_job.user,
                    notif_type="report_ready",
                    level="info",
                    title="Your report is ready",
                    message=(
                        "Go to your reports page to download the report."
                    ),
                    entity=locked_job,
                    meta={
                        "report_type": locked_job.report_type,
                        "report_public_id": locked_job.public_id,
                    },
                )
                locked_job.notification_sent = True
                locked_job.save(update_fields=["notification_sent"])

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"ReportJob {job.public_id} completed"
        return {"status": "done", "report_file": stored_report_name}

    except JobLeaseLost:
        if stored_report_name:
            try:
                delete_report(stored_report_name)
            except Exception:
                logger.exception(
                    "report_lease_lost_object_cleanup_failed",
                    extra={"job_id": getattr(job, "id", None)},
                )
        run.status = ScheduledTaskRun.Status.SKIPPED
        run.message = "Report execution lease was released."
        logger.warning(
            "generate_report_task_lease_lost",
            extra={
                "job_id": getattr(job, "id", report_job_id),
                "task_id": task_id,
            },
        )
        return {"status": "lease_lost"}

    except Exception as exc:
        logger.exception(
            "generate_report_task_failed",
            extra={
                "job_id": getattr(job, "id", None),
                "report_type": getattr(job, "report_type", None),
                "user_id": getattr(job, "user_id", None),
                "task_id": task_id,
            },
        )

        if stored_report_name:
            try:
                delete_report(stored_report_name)
            except Exception:
                logger.exception(
                    "failed_report_object_cleanup_failed",
                    extra={
                        "job_id": getattr(job, "id", None),
                        "report_file": stored_report_name,
                    },
                )

        retries = int(getattr(self.request, "retries", 0) or 0)
        if (
            is_transient_task_error(exc)
            and retries < settings.REPORT_TASK_MAX_RETRIES
        ):
            lease_owned = True
            if job is not None:
                try:
                    lease_owned = prepare_job_retry(job.id, task_id)
                except Exception:
                    # A retry uses the same task id. If the database is
                    # temporarily unavailable, the next delivery can safely
                    # resume this lease or skip itself after a takeover.
                    lease_owned = True
                    logger.exception(
                        "report_retry_lease_refresh_failed",
                        extra={"job_id": job.id, "task_id": task_id},
                    )

            if lease_owned:
                if run is not None:
                    run.status = ScheduledTaskRun.Status.SKIPPED
                    run.message = (
                        "Transient report failure; retry scheduled."
                    )
                raise self.retry(
                    exc=exc,
                    countdown=retry_countdown(self),
                )

        if job is not None:
            mark_job_failed(
                job.id,
                task_id,
                message=REPORT_FAILURE_MESSAGE,
            )

        if run is not None:
            run.status = ScheduledTaskRun.Status.FAILED
            run.message = REPORT_FAILURE_MESSAGE
        raise

    finally:
        if run is not None:
            run.duration_ms = int((time.monotonic() - start_ts) * 1000)
            try:
                run.save()
            except Exception:
                # Audit persistence must never replace the job result or a
                # Celery Retry exception with a secondary database error.
                logger.exception(
                    "generate_report_task_run_log_save_failed",
                    extra={"job_id": getattr(job, "id", report_job_id)},
                )

import io
import json
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from core.mixins import NotificationMixin
from django.conf import settings
import redis
import time
from core.models.tasks import ScheduledTaskRun
from reporting.report_registry import REPORT_DEFINITIONS
from reporting.models.reports import ReportJob
from reporting.utils.excel_renderer import render_workbook, render_workbook_streaming
from reporting.utils.report_payload import wrap_report_payload

redis_reports_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)

from datetime import datetime
from django.utils.timezone import is_aware

import logging
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

def normalize_datetimes(obj):
    """
    Recursively remove timezone information from datetime objects.

    Excel (openpyxl) cannot handle timezone-aware datetimes, so
    any tz-aware datetime must be converted to a naive datetime.

    This function walks nested structures (dicts/lists) and
    normalizes any datetime values found.
    """
    if isinstance(obj, dict):
        return {k: normalize_datetimes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_datetimes(v) for v in obj]
    if isinstance(obj, datetime):
        if is_aware(obj):
            return obj.replace(tzinfo=None)
        return obj
    return obj
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def generate_report_task(self, report_job_id: int):
    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="generate_report_task",
        status=ScheduledTaskRun.Status.STARTED,
    )

    notifier = NotificationMixin()
    job = None

    try:
        job = ReportJob.objects.select_related("user").get(id=report_job_id)

        definition = REPORT_DEFINITIONS.get(job.report_type)
        if not definition:
            raise RuntimeError(f"Unknown report type: {job.report_type}")

        builder = definition["builder"]
        renderer = definition["renderer"]

        # ---------------------------------
        # Mark job running
        # ---------------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.RUNNING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

        # ---------------------------------
        # Build payload
        # ---------------------------------
        builder_params = definition["param_map"](job.params, job.user)

        if job.report_type == ReportJob.ReportType.ASSET_IMPORT:
            payload = job.result_payload
        else:
            payload = builder(**builder_params)

        payload = normalize_datetimes(payload)

        if payload is None:
            raise RuntimeError("Report payload is empty")

        # ---------------------------------
        # Enforce schema
        # ---------------------------------
        if not isinstance(payload, dict):
            raise RuntimeError("Report payload must be a dict")

        if "meta" not in payload:
            raise RuntimeError("Report payload missing 'meta'")

        if "data" not in payload:
            raise RuntimeError("Report payload missing 'data'")

        if not isinstance(payload["meta"], dict):
            raise RuntimeError("'meta' must be a dict")

        if not isinstance(payload["data"], dict):
            raise RuntimeError("'data' must be a dict")

        payload["meta"].setdefault("report_type", job.report_type)
        payload["meta"].setdefault("generated_by", job.user.get_username())
        payload["meta"].setdefault("schema_version", 1)

        # ---------------------------------
        # Render workbook
        # ---------------------------------
        workbook_spec = renderer(payload)

        if definition.get("streaming", False):
            wb = render_workbook_streaming(workbook_spec)
        else:
            wb = render_workbook(workbook_spec)

        # ---------------------------------
        # Save file
        # ---------------------------------
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = settings.REPORT_FILENAME_TEMPLATE.format(
            report_type=job.report_type,
            public_id=job.public_id,
        )
        filename = f"{filename}.xlsx"

        file_path = settings.REPORTS_DIR / filename

        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())

        job.report_file = filename

        # ---------------------------------
        # Mark complete
        # ---------------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()

            job.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "report_file",
                ]
            )

            if not job.notification_sent:
                notifier.notify(
                    recipient=job.user,
                    notif_type="report_ready",
                    level="info",
                    title="Your report is ready",
                    message="Go to your reports page to download the report.",
                    entity=job,
                    meta={
                        "report_type": job.report_type,
                        "report_public_id": job.public_id,
                    },
                )

                job.notification_sent = True
                job.save(update_fields=["notification_sent"])

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"ReportJob {job.public_id} completed"

    except Exception as exc:
        logger.exception(
            "generate_report_task_failed",
            extra={
                "job_id": getattr(job, "id", None),
                "report_type": getattr(job, "report_type", None),
                "user_id": getattr(job, "user_id", None),
            },
        )

        if job:
            with transaction.atomic():
                job.status = ReportJob.Status.FAILED
                job.error = str(exc)
                job.finished_at = timezone.now()
                job.save(update_fields=["status", "error", "finished_at"])

        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)

        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()
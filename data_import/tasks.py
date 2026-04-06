import json
import time

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import redis

from data_import.services.import_builder import build_asset_import
from db_inventory.mixins import NotificationMixin
from db_inventory.models.security import Notification, ScheduledTaskRun
from inventory_metrics.models.reports import ReportJob
from inventory_metrics.utils.report_payload import wrap_report_payload

redis_reports_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def run_asset_import_task(self, report_job_id: int):
    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="run_asset_import",
        status=ScheduledTaskRun.Status.STARTED,
    )

    notifier = NotificationMixin()
    job = None

    try:
        job = ReportJob.objects.select_related("user").get(id=report_job_id)

        # -----------------------------
        # Mark RUNNING
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.RUNNING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

        params = job.params

        if params.get("job_type") != "asset_import":
            raise RuntimeError("ReportJob is not an asset import job.")

        asset_type = params["asset_type"]
        stored_file_name = params["stored_file_name"]

        # -----------------------------
        # Run Import
        # -----------------------------
        raw_data = build_asset_import(
            asset_type=asset_type,
            stored_file_name=stored_file_name,
            generated_by=job.user,
        )

        if not raw_data:
            raise RuntimeError("Import payload is empty")

        issues = raw_data.get("issues", [])

        # -----------------------------
        # Build CSV error report (KISS)
        # -----------------------------
        import csv
        import io

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)

        writer.writerow(["row_number", "status", "reason"])

        for issue in issues:
            writer.writerow([
                issue.get("row_number"),
                issue.get("status"),
                issue.get("reason"),
            ])

        error_csv = csv_buffer.getvalue()

        # -----------------------------
        # Build Redis payload
        # -----------------------------
        payload = wrap_report_payload(
            report_type="asset_import",
            data={
                "summary": raw_data.get("summary", {}),
                "has_error_report": bool(issues),
            },
        )

        redis_key = f"report:{job.public_id}"

        redis_reports_client.setex(
            redis_key,
            settings.REPORT_CACHE_TTL_SECONDS,
            json.dumps(payload, default=str),
        )

        # -----------------------------
        # Mark DONE + store error CSV
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()
            job.error_report_csv = error_csv
            job.save(update_fields=["status", "finished_at", "error_report_csv"])

            if not job.notification_sent:
                notifier.notify(
                    recipient=job.user,
                    notif_type=Notification.NotificationType.REPORT_READY,
                    level=Notification.Level.INFO,
                    title="Your asset import is complete",
                    message="Click to review your import summary.",
                    entity=job,
                    meta={
                        "report_type": "asset_import",
                    },
                )

                job.notification_sent = True
                job.save(update_fields=["notification_sent"])

        # -----------------------------
        # Mark SUCCESS
        # -----------------------------
        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"Import ReportJob {job.public_id} completed"

    except Exception as exc:

        # -----------------------------
        # Mark FAILED
        # -----------------------------
        if job is not None:
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
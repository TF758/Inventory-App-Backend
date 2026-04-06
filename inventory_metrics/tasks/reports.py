import io
import json
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from db_inventory.mixins import NotificationMixin
from inventory_metrics.utils.excel_renderer import render_workbook
from inventory_metrics.viewsets.general import REPORT_RENDERERS
from inventory_metrics.utils.report_payload import wrap_report_payload
from inventory_metrics.services.site_reports import build_site_asset_report, build_site_audit_log_report
from inventory_metrics.models import ReportJob
from inventory_metrics.services.user_summary import build_user_summary_report
from django.conf import settings
import redis
from inventory_metrics.redis import redis_reports_client
from db_inventory.models.security import Notification, ScheduledTaskRun
import time
from django.db import DatabaseError

redis_reports_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)

from datetime import datetime
from django.utils.timezone import is_aware

def normalize_datetimes(obj):
    if isinstance(obj, dict):
        return {k: normalize_datetimes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_datetimes(v) for v in obj]
    if isinstance(obj, datetime):
        if is_aware(obj):
            return obj.replace(tzinfo=None)
        return obj
    return obj


@shared_task(
    bind=True,
    autoretry_for=(DatabaseError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_user_summary_report_task(self, report_job_id: int):
    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="generate_user_summary_report",
        status=ScheduledTaskRun.Status.STARTED,
    )

    notifier = NotificationMixin()

    try:
        job = ReportJob.objects.select_related("user").get(id=report_job_id)

        # -----------------------------
        # Mark RUNNING
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.RUNNING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

        # -----------------------------
        # Build report data
        # -----------------------------
        raw_data = build_user_summary_report(
            user_identifier=job.params["user"],
            sections=job.params["sections"],
        )

        clean_data = normalize_datetimes(raw_data)

        payload = wrap_report_payload(
            report_type="user_summary",
            data=clean_data,
        )

        # -----------------------------
        # Render XLSX
        # -----------------------------
        renderer_cfg = REPORT_RENDERERS.get(job.report_type)
        renderer = renderer_cfg.get("xlsx")

        if not renderer:
            raise RuntimeError("No XLSX renderer configured for report.")

        workbook_spec = renderer(payload["data"])
        wb = render_workbook(workbook_spec)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # -----------------------------
        # Save file to REPORTS_DIR
        # -----------------------------
        filename = settings.REPORT_FILENAME_TEMPLATE.format(
            report_type=job.report_type,
            public_id=job.public_id,
        )
        filename = f"{filename}.xlsx"

        file_path = settings.REPORTS_DIR / filename

        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())

        # Save filename reference
        job.report_file = filename
        job.save(update_fields=["report_file"])

        # -----------------------------
        # Mark DONE + notify
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])

            if not job.notification_sent:
                notifier.notify(
                    recipient=job.user,
                    notif_type=Notification.NotificationType.REPORT_READY,
                    level=Notification.Level.INFO,
                    title="Your report is ready",
                    message="Click to download your report.",
                    entity=job,
                    meta={
                        "report_type": "user_summary",
                        "formats": ["xlsx"],
                    },
                )

                job.notification_sent = True
                job.save(update_fields=["notification_sent"])

        # -----------------------------
        # Mark SUCCESS
        # -----------------------------
        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"ReportJob {job.public_id} completed"

    except Exception as exc:

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



@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def generate_site_asset_report_task(self, report_job_id: int):
    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="generate_site_asset_report",
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

        # -----------------------------
        # Build payload
        # -----------------------------
        params = job.params
        site = params["site"]
        asset_types = params["asset_types"]

        raw_data = build_site_asset_report(
            site_type=site["siteType"],
            site_id=site["siteId"],
            asset_types=asset_types,
            generated_by=job.user,
        )

        if not raw_data:
            raise RuntimeError("Site asset report payload is empty")

        payload = wrap_report_payload(
            report_type="site_assets",
            data=raw_data,
        )

        if payload is None:
            raise RuntimeError("Site asset report payload is empty")

        redis_key = f"report:{job.public_id}"

        redis_reports_client.setex(
            redis_key,
            settings.REPORT_CACHE_TTL_SECONDS,
            json.dumps(payload, default=str),
        )

        # -----------------------------
        # Mark DONE + notify
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])

            if not job.notification_sent:
                notifier.notify(
                    recipient=job.user,
                    notif_type=Notification.NotificationType.REPORT_READY,
                    level=Notification.Level.INFO,
                    title="Your site asset report is ready",
                    message="Click to download your report.",
                    entity=job,
                    meta={
                        "report_type": "site_assets",
                        "formats": ["xlsx"],
                    },
                )
                job.notification_sent = True
                job.save(update_fields=["notification_sent"])

        # -----------------------------
        # Mark task SUCCESS
        # -----------------------------
        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"ReportJob {job.public_id} completed"

    except Exception as exc:
        # -----------------------------
        # Mark FAILED (guarded)
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

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def generate_site_audit_log_report_task(self, report_job_id: int):
    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="generate_site_audit_log_report",
        status=ScheduledTaskRun.Status.STARTED,
        message=f"ReportJob id={report_job_id}",
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

        # -----------------------------
        # Build payload
        # -----------------------------
        params = job.params

        raw_data = build_site_audit_log_report(
            site=params["site"],
            audit_period_days=params.get("audit_period_days", 30),
            generated_by=job.user,
        )

        if not raw_data:
            raise RuntimeError("Site audit log report payload is empty")

        payload = wrap_report_payload(
            report_type="site_audit_logs",
            data=raw_data,
        )

        redis_key = f"report:{job.public_id}"

        redis_reports_client.setex(
            redis_key,
            settings.REPORT_CACHE_TTL_SECONDS,
            json.dumps(payload, default=str),
        )

        # -----------------------------
        # Mark DONE + notify
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])

            if not job.notification_sent:
                notifier.notify(
                    recipient=job.user,
                    notif_type=Notification.NotificationType.REPORT_READY,
                    level=Notification.Level.INFO,
                    title="Your audit log report is ready",
                    message="Click to download your report.",
                    entity=job,
                    meta={
                        "report_type": "site_audit_logs",
                        "formats": ["xlsx", "json"],
                    },
                )
                job.notification_sent = True
                job.save(update_fields=["notification_sent"])

        # -----------------------------
        # Mark task SUCCESS
        # -----------------------------
        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"ReportJob {job.public_id} completed"

    except Exception as exc:
        # -----------------------------
        # Mark FAILED (guarded)
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



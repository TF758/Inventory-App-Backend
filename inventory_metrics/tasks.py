import json
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from db_inventory.mixins import NotificationMixin
from db_inventory.models.site import Department
from inventory_metrics.utils.report_payload import wrap_report_payload
from inventory_metrics.services.snapshots import generate_daily_auth_metrics, generate_daily_department_snapshot, generate_daily_system_metrics
from inventory_metrics.services.site_reports import build_site_asset_report, build_site_audit_log_report
from inventory_metrics.models import ReportJob
from inventory_metrics.services.user_summary import build_user_summary_report
from django.conf import settings
import redis
from inventory_metrics.redis import redis_reports_client
from db_inventory.models.security import Notification, ScheduledTaskRun
import time


redis_reports_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
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
        # Mark RUNNING (business state)
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.RUNNING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

        # -----------------------------
        # Build payload
        # -----------------------------

        raw_data = build_user_summary_report(
            user_identifier=job.params["user"],
            sections=job.params["sections"],
        )
        payload = wrap_report_payload(
            report_type="user_summary",
            data=raw_data,
        )

        redis_key = f"report:{job.public_id}"

        # -----------------------------
        # Cache in Redis
        # -----------------------------
        redis_reports_client.setex(
            redis_key,
            job.cache_ttl_seconds,
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
                    title="Your report is ready",
                    message="Click to download your report.",
                    entity=job,
                    meta={
                        "report_type": "user_summary",
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
        # Mark FAILED (both layers)
        # -----------------------------
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
        related_object=f"ReportJob:{report_job_id}",
    )

    notifier = NotificationMixin()

    try:
        job = ReportJob.objects.select_related("user").get(id=report_job_id)

        # -----------------------------
        # Mark RUNNING (business state)
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
        # Mark FAILED (both layers)
        # -----------------------------
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
        related_object=f"ReportJob:{report_job_id}",
    )

    notifier = NotificationMixin()

    try:
        job = ReportJob.objects.select_related("user").get(id=report_job_id)

        # -----------------------------
        # Mark RUNNING (business state)
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
        # Mark FAILED (both layers)
        # -----------------------------
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


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def run_daily_system_metrics_snapshot(self):
    start = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="daily_system_metrics_snapshot",
        status=ScheduledTaskRun.Status.STARTED,
        schema_version=settings.SNAPSHOT_SCHEMA_VERSION,
    )

    try:
        created = generate_daily_system_metrics()

        run.status = (
            ScheduledTaskRun.Status.SUCCESS
            if created
            else ScheduledTaskRun.Status.SKIPPED
        )
        run.message = "Snapshot created" if created else "Snapshot already exists"

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save()

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def run_daily_department_snapshots(self):
    """
    Generate daily snapshots for all departments.
    Safe to run multiple times per day (idempotent).
    """

    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="run_daily_department_snapshots",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting department snapshot generation",
    )

    created_count = 0
    skipped_count = 0
    error_count = 0

    try:
        departments = Department.objects.all()

        for department in departments:
            try:
                created = generate_daily_department_snapshot(
                    department=department,
                    snapshot_date=timezone.localdate(),
                    created_by="celery",
                )

                if created:
                    created_count += 1
                else:
                    skipped_count += 1

            except Exception as exc:
                # Do NOT fail the entire task for one bad department
                error_count += 1

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = (
            f"Departments processed={departments.count()}, "
            f"created={created_count}, "
            f"skipped={skipped_count}, "
            f"errors={error_count}"
        )

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()

@shared_task(bind=True, 
             autoretry_for=(Exception,), 
             retry_kwargs={"max_retries": 3, "countdown": 60})
def run_daily_auth_metrics_snapshot(self):
    start = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="daily_auth_metrics_snapshot",
        status=ScheduledTaskRun.Status.STARTED,
        schema_version=settings.SNAPSHOT_SCHEMA_VERSION,
    )

    try:
        created = generate_daily_auth_metrics()

        run.status = (
            ScheduledTaskRun.Status.SUCCESS
            if created
            else ScheduledTaskRun.Status.SKIPPED
        )
        run.message = "Snapshot created" if created else "Snapshot already exists"

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save()
import json
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from db_inventory.mixins import NotificationMixin
from inventory_metrics.services.site_reports import build_site_asset_report
from inventory_metrics.models import ReportJob
from inventory_metrics.services.user_summary import build_user_summary_report
from django.conf import settings
import redis
from inventory_metrics.redis import redis_reports_client
from db_inventory.models.security import Notification
redis_reports_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)



@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def generate_user_summary_report_task(self, report_job_id: int):
    job = ReportJob.objects.select_related("user").get(id=report_job_id)
    notifier = NotificationMixin()

    # -----------------------------
    # Mark RUNNING
    # -----------------------------
    with transaction.atomic():
        job.status = ReportJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

    try:
        # -----------------------------
        # Build payload
        # -----------------------------
        payload = build_user_summary_report(
            user_identifier=job.params["user"],
            sections=job.params["sections"],
        )

        redis_key = f"report:{job.public_id}"

        # -----------------------------
        # Cache in Redis (DB 2)
        # -----------------------------
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
                title="Your report is ready",
                message="Click to download your report.",
                entity=job,
                meta={
                "report_type": "user_summary",
                "formats": ["xlsx", "json"],
            },)
            job.notification_sent = True
            job.save(update_fields=["notification_sent"])

    except Exception as exc:
        # -----------------------------
        # Mark FAILED
        # -----------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.FAILED
            job.error = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error", "finished_at"])
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def generate_site_asset_report_task(self, report_job_id: int):
    job = ReportJob.objects.select_related("user").get(id=report_job_id)
    notifier = NotificationMixin()

    with transaction.atomic():
        job.status = ReportJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

    try:
        params = job.params
        site = params["site"]
        asset_types = params["asset_types"]

        payload = build_site_asset_report(
            site_type=site["siteType"],
            site_id=site["siteId"],
            asset_types=asset_types,
            generated_by=job.user,
        )

        redis_key = f"report:{job.public_id}"

        redis_reports_client.setex(
            redis_key,
            settings.REPORT_CACHE_TTL_SECONDS,
            json.dumps(payload, default=str),
        )

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

    except Exception as exc:
        with transaction.atomic():
            job.status = ReportJob.Status.FAILED
            job.error = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error", "finished_at"])
        raise

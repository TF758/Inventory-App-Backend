import json
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from db_inventory.mixins import NotificationMixin
from inventory_metrics.models import ReportJob
from inventory_metrics.services.user_summary import build_user_summary_report
from django.conf import settings
import redis


redis_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def generate_user_summary_report_task(self, report_job_id: int):
    job = ReportJob.objects.select_related("user").get(id=report_job_id)
    notifier = NotificationMixin()

    # ---- mark running -------------------------------------------------
    with transaction.atomic():
        job.status = ReportJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

    try:
        # ---- build report payload -------------------------------------
        payload = build_user_summary_report(
            user_identifier=job.params["user"],
            sections=job.params["sections"],
        )

        serialized_payload = json.dumps(payload, default=str)

        redis_key = f"report:{job.public_id}"

        # ---- cache in Redis (TTL handled by Redis) --------------------
        redis_client.setex(
            redis_key,
            settings.REPORT_CACHE_TTL_SECONDS,
            serialized_payload,
        )

        # ---- mark done + notify (after commit) ------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.DONE
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])

            if not job.notification_sent:
                notifier.notify(
                    recipient=job.user,
                    notif_type="report_ready",
                    title="Your report is ready",
                    message="Click to download your report.",
                    entity=job,
                )
                job.notification_sent = True
                job.save(update_fields=["notification_sent"])

    except Exception as exc:
        # ---- mark failed ---------------------------------------------
        with transaction.atomic():
            job.status = ReportJob.Status.FAILED
            job.error = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error", "finished_at"])

        raise
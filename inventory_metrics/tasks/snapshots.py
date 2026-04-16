from celery import shared_task
from django.utils import timezone
from db_inventory.models.site import Department

from django.conf import settings
import redis
from db_inventory.models.security import ScheduledTaskRun
import time
from django.db import DatabaseError

from analytics.services.snapshots import generate_daily_auth_metrics, generate_daily_department_snapshot, generate_daily_return_metrics, generate_daily_system_metrics

redis_reports_client = redis.Redis.from_url(settings.REDIS_REPORTS_URL)



@shared_task(bind=True,  autoretry_for=(DatabaseError,), retry_kwargs={"max_retries": 3, "countdown": 60})
def run_daily_system_metrics_snapshot(self):
    start = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="run_daily_system_metrics_snapshot",
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

@shared_task( bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3}, retry_backoff=True, )
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

@shared_task(
    bind=True,
    autoretry_for=(DatabaseError,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def run_daily_auth_metrics_snapshot(self):
    start = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="run_daily_auth_metrics_snapshot",
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
        run.message = (
            "Auth metrics snapshot created"
            if created
            else "Auth metrics snapshot already exists"
        )

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save()

@shared_task( bind=True, autoretry_for=(DatabaseError,), retry_kwargs={"max_retries": 3, "countdown": 60}, )
def run_daily_return_metrics_snapshot(self):
    start = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="run_daily_return_metrics_snapshot",
        status=ScheduledTaskRun.Status.STARTED,
        schema_version=settings.SNAPSHOT_SCHEMA_VERSION,
    )

    try:
        created = generate_daily_return_metrics()

        run.status = (
            ScheduledTaskRun.Status.SUCCESS
            if created
            else ScheduledTaskRun.Status.SKIPPED
        )

        run.message = (
            "Return metrics snapshot created"
            if created
            else "Return metrics snapshot already exists"
        )

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)
        raise

    finally:
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.save()
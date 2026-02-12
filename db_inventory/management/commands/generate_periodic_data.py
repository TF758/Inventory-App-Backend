import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask

class Command(BaseCommand):
    help = "Setup periodic Celery Beat tasks for automated data generation"

    def handle(self, *args, **options):
        self.stdout.write("Setting up periodic data Celery Beat schedules...")

        def upsert_task(name: str, task: str, cron_expr: str):
            minute, hour, day, month, dow = cron_expr.split()

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_month=day,
                month_of_year=month,
                day_of_week=dow,
                timezone=settings.TIME_ZONE,
            )

            PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task,
                    "crontab": schedule,
                    "enabled": True,
                    "kwargs": json.dumps({}),
                    "date_changed": timezone.now(),
                },
            )

        # ------------------------------------------------------------------
        # Daily system metrics snapshots (automated, non-user tasks)
        # ------------------------------------------------------------------
        upsert_task(
            name="Generate daily system metrics snapshot",
            task="inventory_metrics.tasks.snapshots.run_daily_system_metrics_snapshot",
            cron_expr=settings.DAILY_SYSTEM_METRICS_CRON,
        )

        upsert_task(
            name="Generate daily department snapshots",
            task="inventory_metrics.tasks.snapshots.run_daily_department_snapshots",
            cron_expr=settings.DAILY_SYSTEM_METRICS_CRON,
        )

        upsert_task(
            name="Generate daily auth metrics snapshot",
            task="inventory_metrics.tasks.snapshots.run_daily_auth_metrics_snapshot",
            cron_expr=settings.DAILY_SYSTEM_METRICS_CRON,
        )

        self.stdout.write(
            self.style.SUCCESS("Periodic data Celery Beat tasks configured.")
        )
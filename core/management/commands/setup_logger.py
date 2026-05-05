import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from django_celery_beat.models import (
    CrontabSchedule,
    PeriodicTask,
    IntervalSchedule,
)


class Command(BaseCommand):
    help = "Setup Celery Beat tasks for logging maintenance (archive, cleanup)"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Setting up logging Celery Beat schedules...\n")
        )

        def upsert_cron_task(name: str, task: str, cron_expr: str):
            minute, hour, day, month, dow = cron_expr.split()

            schedule, schedule_created = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_month=day,
                month_of_year=month,
                day_of_week=dow,
                timezone=settings.TIME_ZONE,
            )

            periodic_task, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task,
                    "crontab": schedule,
                    "enabled": True,
                    "kwargs": json.dumps({}),
                    "date_changed": timezone.now(),
                },
            )

            status = "CREATED" if created else "UPDATED"
            schedule_status = "new schedule" if schedule_created else "existing schedule"

            self.stdout.write(
                f"[{status}] {name}\n"
                f"  → task: {task}\n"
                f"  → cron: {cron_expr} ({schedule_status})\n"
            )

        def upsert_interval_task(name: str, task: str, seconds: int):
            schedule, schedule_created = IntervalSchedule.objects.get_or_create(
                every=seconds,
                period=IntervalSchedule.SECONDS,
            )

            periodic_task, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task,
                    "interval": schedule,
                    "enabled": True,
                    "kwargs": json.dumps({}),
                    "date_changed": timezone.now(),
                },
            )

            status = "CREATED" if created else "UPDATED"

            self.stdout.write(
                f"[{status}] {name}\n"
                f"  → task: {task}\n"
                f"  → every: {seconds}s\n"
            )

        # ------------------------------------------------------------------
        # Archive logs task
        # ------------------------------------------------------------------

        if getattr(settings, "LOG_ARCHIVE_USE_INTERVAL", False):
            upsert_interval_task(
                name="Archive logs (interval)",
                task="core.tasks.logging.archive_logs",
                seconds=settings.LOG_ARCHIVE_INTERVAL_SECONDS,
            )
        else:
            upsert_cron_task(
                name="Archive logs (cron)",
                task="core.tasks.logging.archive_logs",
                cron_expr=settings.LOG_ARCHIVE_CRON,
            )

        self.stdout.write(
            self.style.SUCCESS("\n✔ Logging Celery Beat tasks configured successfully.")
        )
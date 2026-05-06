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
            self.style.WARNING(
                "Setting up logging Celery Beat schedules...\n"
            )
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

            periodic_task, created = (
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
            )

            status = "CREATED" if created else "UPDATED"
            schedule_status = (
                "new schedule"
                if schedule_created
                else "existing schedule"
            )

            self.stdout.write(
                f"[{status}] {name}\n"
                f"  → task: {task}\n"
                f"  → cron: {cron_expr} ({schedule_status})\n"
            )
        # ------------------------------------------------------------------
        # Archive logs task
        # ------------------------------------------------------------------

        upsert_cron_task(
            name="Archive logs (cron)",
            task="core.tasks.archive_logs.archive_logs",
            cron_expr=settings.LOG_ARCHIVE_CRON,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n✔ Logging Celery Beat tasks configured successfully."
            )
        )
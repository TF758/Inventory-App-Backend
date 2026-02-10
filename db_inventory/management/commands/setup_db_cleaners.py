from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.conf import settings
import json
from django.utils import timezone
class Command(BaseCommand):
    help = "Setup DB maintenance Celery Beat tasks (cleanup / pruning)"

    def handle(self, *args, **options):
        self.stdout.write(
            "Setting up DB maintenance Celery Beat schedules..."
        )

        def upsert_task(name, task, cron_expr):
            try:
                minute, hour, day, month, dow = cron_expr.split()
            except ValueError:
                raise ValueError(
                    f"Invalid cron expression for {name}: {cron_expr}"
                )

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

        # -------------------------------
        # DB maintenance tasks
        # -------------------------------
        upsert_task(
            name="DB Maintenance: cleanup notifications",
            task="db_inventory.tasks.cleanup_notifications",
            cron_expr=settings.NOTIF_CLEANUP_CRON,
        )

        upsert_task(
            name="DB Maintenance: cleanup scheduled task runs",
            task="db_inventory.tasks.cleanup_scheduled_task_runs",
            cron_expr=settings.TASKRUN_CLEANUP_CRON,
        )

        upsert_task(
        name="DB Maintenance: cleanup user sessions",
        task="db_inventory.tasks.cleanup_user_sessions",
        cron_expr=settings.USERSESSION_CLEANUP_CRON,
        )

        self.stdout.write(
            self.style.SUCCESS("DB maintenance beat tasks configured.")
        )
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
        # Notification lifecycle
        # -------------------------------
        upsert_task(
            name="01 Auto-read stale notifications",
            task="core.tasks.cleanup.auto_read_stale_notifications",
            cron_expr=settings.NOTIF_AUTO_READ_CRON,
        )

        upsert_task(
            name="01 Auto-soft-delete notifications",
            task="core.tasks.cleanup.auto_soft_delete_notifications",
            cron_expr=settings.NOTIF_SOFT_DELETE_CRON,
        )

        upsert_task(
            name="01 DB Maintenance: cleanup notifications",
            task="core.tasks.cleanup.cleanup_notifications",
            cron_expr=settings.NOTIF_CLEANUP_CRON,
        )

        # -------------------------------
        # Session lifecycle
        # -------------------------------
        upsert_task(
            name="DB Maintenance: expire user sessions",
            task="core.tasks.cleanup.expire_user_sessions",
            cron_expr=settings.USERSESSION_EXPIRE_CRON,
        )

        upsert_task(
            name="DB Maintenance: cleanup user sessions",
            task="core.tasks.cleanup.cleanup_user_sessions",
            cron_expr=settings.USERSESSION_CLEANUP_CRON,
        )

        # -------------------------------
        # Internal maintenance
        # -------------------------------
        upsert_task(
            name="DB Maintenance: cleanup scheduled task runs",
            task="core.tasks.cleanup.cleanup_scheduled_task_runs",
            cron_expr=settings.TASKRUN_CLEANUP_CRON,
        )


        # -------------------------------
        # Report lifecycle
        # -------------------------------
        upsert_task(
            name="DB Maintenance: delete old reports",
            task="analytics.tasks.cleanup.delete_old_reports",
            cron_expr=settings.REPORT_DELETE_CRON,
        )

        self.stdout.write(
            self.style.SUCCESS("DB maintenance beat tasks configured.")
        )
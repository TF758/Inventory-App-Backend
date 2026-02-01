from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.conf import settings
import json
from django.utils import timezone

class Command(BaseCommand):
    help = "Setup notification cleanup celery beat tasks"

    def handle(self, *args, **options):
        self.stdout.write("Setting up notification Celery Beat schedules...")

        def upsert_task(name, task, cron_expr):
            minute, hour, day, month, dow = cron_expr.split()

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_month=day,
                month_of_year=month,
                day_of_week=dow,
                timezone=settings.TIME_ZONE,  # ✅ FIX #1
            )

            PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task,
                    "crontab": schedule,
                    "enabled": True,
                    "kwargs": json.dumps({}),
                    "date_changed": timezone.now(),  # ✅ FIX #2
                },
            )

        upsert_task(
            name="Auto-read stale notifications",
            task="db_inventory.tasks.auto_read_stale_notifications",
            cron_expr=settings.NOTIF_AUTO_READ_CRON,
        )

        upsert_task(
            name="Cleanup notifications",
            task="db_inventory.tasks.cleanup_notifications",
            cron_expr=settings.NOTIF_CLEANUP_CRON,
        )

        self.stdout.write(self.style.SUCCESS("Notification beat tasks configured."))
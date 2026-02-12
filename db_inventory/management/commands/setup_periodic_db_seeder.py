from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.conf import settings
import json
from django.utils import timezone
class Command(BaseCommand):
    help = "Setup simulation Celery Beat tasks (data generation)"

    def handle(self, *args, **options):
        self.stdout.write(
            "Setting up simulation Celery Beat schedules..."
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

        upsert_task(
            name="Simulation: generate notifications",
            task="db_inventory.tasks.generate_data.generate_notifications",
            cron_expr="*/10 * * * *",
        )

        upsert_task(
            name="Simulation: generate user sessions",
            task="db_inventory.tasks.generate_data.generate_user_sessions",
            cron_expr="*/15 * * * *",
        )

        self.stdout.write(
            self.style.SUCCESS("Simulation beat tasks configured.")
        )
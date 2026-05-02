import json
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Setup DB maintenance Celery Beat tasks (cleanup / pruning)"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Setting up DB maintenance Celery Beat schedules...\n")
        )

        created_count = 0
        updated_count = 0

        def upsert_task(name, task, cron_expr):
            nonlocal created_count, updated_count

            try:
                minute, hour, day, month, dow = cron_expr.split()
            except ValueError:
                raise ValueError(f"Invalid cron expression for {name}: {cron_expr}")

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

            if created:
                created_count += 1
            else:
                updated_count += 1

            status = "CREATED" if created else "UPDATED"
            schedule_status = "new schedule" if schedule_created else "existing schedule"

            self.stdout.write(
                f"[{status}] {name}\n"
                f"  → task: {task}\n"
                f"  → cron: {cron_expr} ({schedule_status})\n"
            )

        # -------------------------------
        # Notification lifecycle
        # -------------------------------
        self.stdout.write(self.style.NOTICE("→ Notification lifecycle"))

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
        self.stdout.write(self.style.NOTICE("→ Session lifecycle"))

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
        self.stdout.write(self.style.NOTICE("→ Internal maintenance"))

        upsert_task(
            name="DB Maintenance: cleanup scheduled task runs",
            task="core.tasks.cleanup.cleanup_scheduled_task_runs",
            cron_expr=settings.TASKRUN_CLEANUP_CRON,
        )

        # -------------------------------
        # Report lifecycle
        # -------------------------------
        self.stdout.write(self.style.NOTICE("→ Report lifecycle"))

        upsert_task(
            name="DB Maintenance: delete old reports",
            task="analytics.tasks.cleanup.delete_old_reports",
            cron_expr=settings.REPORT_DELETE_CRON,
        )

        # -------------------------------
        # Summary
        # -------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✔ DB maintenance beat tasks configured "
                f"({created_count} created, {updated_count} updated)."
            )
        )
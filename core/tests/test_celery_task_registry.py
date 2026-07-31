from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django_celery_beat.models import (
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
)


class CeleryTaskRegistryCommandTests(TestCase):
    def setUp(self):
        self.schedule = IntervalSchedule.objects.create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )

    def test_registered_beat_task_passes(self):
        PeriodicTask.objects.create(
            name="Recover jobs",
            task="core.tasks.job_recovery.recover_stale_report_jobs",
            interval=self.schedule,
            enabled=True,
        )
        output = StringIO()

        call_command("check_celery_tasks", stdout=output)

        self.assertIn("1 enabled Beat entries checked", output.getvalue())

    def test_setup_logger_repairs_legacy_archive_task_path(self):
        legacy_schedule = CrontabSchedule.objects.create(
            minute="0",
            hour="0",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone="UTC",
        )
        periodic_task = PeriodicTask.objects.create(
            name="Archive logs (cron)",
            task="core.tasks.archive_logs.archive_logs",
            crontab=legacy_schedule,
            enabled=True,
        )

        call_command("setup_logger", stdout=StringIO())

        periodic_task.refresh_from_db()
        self.assertEqual(
            periodic_task.task,
            "core.tasks.logs.archive_logs",
        )
        call_command("check_celery_tasks")

    def test_unknown_enabled_beat_task_fails(self):
        PeriodicTask.objects.create(
            name="Typo task",
            task="core.tasks.job_recovery.missing_task",
            interval=self.schedule,
            enabled=True,
        )

        with self.assertRaises(CommandError):
            call_command("check_celery_tasks")

    def test_disabled_unknown_task_is_ignored(self):
        PeriodicTask.objects.create(
            name="Old disabled task",
            task="legacy.tasks.removed",
            interval=self.schedule,
            enabled=False,
        )

        call_command("check_celery_tasks")

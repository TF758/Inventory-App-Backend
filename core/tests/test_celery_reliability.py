from django.conf import settings
from django.test import SimpleTestCase

from core.tasks.job_recovery import recover_stale_report_jobs
from data_import.tasks import run_asset_import_task
from reporting.tasks.reports import generate_report_task


class CeleryReliabilitySettingsTests(SimpleTestCase):
    def test_long_running_jobs_use_late_acknowledgement(self):
        for task in (
            run_asset_import_task,
            generate_report_task,
            recover_stale_report_jobs,
        ):
            self.assertTrue(task.acks_late)
            self.assertTrue(task.reject_on_worker_lost)

        self.assertEqual(settings.CELERY_WORKER_PREFETCH_MULTIPLIER, 1)

    def test_import_report_and_recovery_tasks_have_separate_routes(self):
        routes = settings.CELERY_TASK_ROUTES
        self.assertEqual(
            routes["data_import.tasks.*"]["queue"],
            "imports",
        )
        self.assertEqual(
            routes["reporting.tasks.*"]["queue"],
            "reports",
        )
        self.assertEqual(
            routes["core.tasks.job_recovery.*"]["queue"],
            "maintenance",
        )

    def test_stale_threshold_exceeds_job_hard_limits(self):
        self.assertLess(
            settings.IMPORT_TASK_SOFT_TIME_LIMIT,
            settings.IMPORT_TASK_TIME_LIMIT,
        )
        self.assertLess(
            settings.REPORT_TASK_SOFT_TIME_LIMIT,
            settings.REPORT_TASK_TIME_LIMIT,
        )
        self.assertGreater(
            settings.JOB_STALE_AFTER_SECONDS,
            max(
                settings.IMPORT_TASK_TIME_LIMIT,
                settings.REPORT_TASK_TIME_LIMIT,
                settings.TASK_RETRY_MAX_DELAY_SECONDS,
            ),
        )

    def test_attempt_budget_covers_configured_retries(self):
        self.assertGreaterEqual(
            settings.JOB_MAX_ATTEMPTS,
            max(
                settings.IMPORT_TASK_MAX_RETRIES,
                settings.REPORT_TASK_MAX_RETRIES,
            ) + 1,
        )

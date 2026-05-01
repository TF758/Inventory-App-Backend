from django.test import TestCase
from unittest.mock import patch
from django.utils import timezone

from analytics.tasks.snapshots import run_daily_auth_metrics_snapshot, run_daily_return_metrics_snapshot, run_daily_system_metrics_snapshot
from core.models.tasks import ScheduledTaskRun


class TestSnapshotTasks(TestCase):

    # -------------------------
    # Generic helpers
    # -------------------------

    def assert_run_created(self, task_name, status):
        run = ScheduledTaskRun.objects.first()
        self.assertIsNotNone(run)
        self.assertEqual(run.task_name, task_name)
        self.assertEqual(run.status, status)
        self.assertIsNotNone(run.duration_ms)

    # -------------------------
    # AUTH METRICS TASK
    # -------------------------

    def test_auth_task_success(self):
        with patch("analytics.tasks.generate_daily_auth_metrics", return_value=True):
            run_daily_auth_metrics_snapshot.run()

        self.assert_run_created(
            "run_daily_auth_metrics_snapshot",
            ScheduledTaskRun.Status.SUCCESS,
        )
        
    def test_auth_task_skipped(self):
        with patch("analytics.tasks.snapshots.generate_daily_auth_metrics", return_value=False):
            run_daily_auth_metrics_snapshot.run()

        self.assert_run_created(
            "run_daily_auth_metrics_snapshot",
            ScheduledTaskRun.Status.SKIPPED,
        )

    def test_auth_task_failure(self):
        with patch("analytics.tasks.snapshots.generate_daily_auth_metrics", side_effect=Exception("boom")):
            try:
                run_daily_auth_metrics_snapshot.run()
            except Exception:
                pass  # expected behavior under Celery retry

        run = ScheduledTaskRun.objects.first()
        self.assertEqual(run.status, ScheduledTaskRun.Status.FAILED)

    # -------------------------
    # SYSTEM METRICS TASK
    # -------------------------

    def test_system_task_success(self):
        with patch("analytics.tasks.generate_daily_system_metrics", return_value=True):
            run_daily_system_metrics_snapshot.run()

        self.assert_run_created(
            "run_daily_system_metrics_snapshot",
            ScheduledTaskRun.Status.SUCCESS,
        )

    # -------------------------
    # RETURN METRICS TASK
    # -------------------------

    def test_return_task_success(self):
        with patch("analytics.tasks.generate_daily_return_metrics", return_value=True):
            run_daily_return_metrics_snapshot()

        self.assert_run_created(
            "run_daily_return_metrics_snapshot",
            ScheduledTaskRun.Status.SUCCESS,
        )

    # -------------------------
    # IDENTITY / SAFETY
    # -------------------------

    def test_tasks_are_idempotent_safe(self):
        with patch("analytics.tasks.generate_daily_auth_metrics", return_value=False):
            run_daily_auth_metrics_snapshot.run()
            run_daily_auth_metrics_snapshot.run()

        self.assertEqual(ScheduledTaskRun.objects.count(), 2)
from unittest.mock import patch
from celery.exceptions import Retry

from django.test import TestCase
from django.db import OperationalError
from django.utils import timezone

from reporting.models.reports import ReportJob
from reporting.services.storage import (
    delete_report,
    report_download_name,
    report_exists,
)
from reporting.tasks.reports import generate_report_task
from users.factories.user_factories import UserFactory


class FakeWorkbook:
    def save(self, output):
        output.write(b"fake workbook")


class ReportTaskReliabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def make_job(self, **overrides):
        values = {
            "user": self.user,
            "report_type": ReportJob.ReportType.USER_SUMMARY,
            "params": {},
        }
        values.update(overrides)
        return ReportJob.objects.create(**values)

    def tearDown(self):
        for name in ReportJob.objects.exclude(report_file="").values_list(
            "report_file",
            flat=True,
        ):
            delete_report(name)

    @patch("reporting.tasks.reports.NotificationMixin.notify")
    @patch("reporting.tasks.reports.render_workbook")
    @patch.dict(
        "reporting.tasks.reports.REPORT_DEFINITIONS",
        {
            ReportJob.ReportType.USER_SUMMARY: {
                "builder": lambda **kwargs: {"meta": {}, "data": {}},
                "renderer": lambda payload: {},
                "param_map": lambda params, user: {},
            }
        },
        clear=True,
    )
    def test_successful_report_releases_lease_and_persists_object(
        self,
        mock_render,
        mock_notify,
    ):
        mock_render.return_value = FakeWorkbook()
        job = self.make_job()

        result = generate_report_task.apply(
            args=[job.id],
            task_id="report-task-one",
            throw=True,
        ).get()

        self.assertEqual(result["status"], "done")
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.DONE)
        self.assertEqual(job.task_id, "")
        self.assertIsNone(job.heartbeat_at)
        self.assertEqual(job.attempt_count, 1)
        self.assertTrue(report_exists(job.report_file))
        self.assertIn("/report-task-one/", job.report_file)
        self.assertNotIn(
            "report-task-one",
            report_download_name(job.report_file),
        )
        mock_notify.assert_called_once()

    @patch(
        "reporting.tasks.reports.generate_report_task.retry",
        side_effect=Retry(),
    )
    @patch.dict(
        "reporting.tasks.reports.REPORT_DEFINITIONS",
        {
            ReportJob.ReportType.USER_SUMMARY: {
                "builder": lambda **kwargs: (_ for _ in ()).throw(
                    OperationalError("database temporarily unavailable")
                ),
                "renderer": lambda payload: {},
                "param_map": lambda params, user: {},
            }
        },
        clear=True,
    )
    def test_transient_report_failure_keeps_lease_for_retry(
        self,
        mock_retry,
    ):
        job = self.make_job()

        with self.assertRaises(Retry):
            generate_report_task.run(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.RUNNING)
        self.assertTrue(job.task_id)
        self.assertIsNotNone(job.heartbeat_at)
        self.assertEqual(job.attempt_count, 2)
        mock_retry.assert_called_once()

    @patch(
        "reporting.tasks.reports.generate_report_task.retry",
        side_effect=Retry(),
    )
    @patch(
        "reporting.tasks.reports.claim_job",
        side_effect=OperationalError("database temporarily unavailable"),
    )
    def test_transient_claim_failure_is_retried(
        self,
        mock_claim_job,
        mock_retry,
    ):
        with self.assertRaises(Retry):
            generate_report_task.run(999999)

        mock_claim_job.assert_called_once()
        mock_retry.assert_called_once()

    @patch.dict(
        "reporting.tasks.reports.REPORT_DEFINITIONS",
        {},
        clear=True,
    )
    def test_active_duplicate_delivery_is_skipped(self):
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="active-task",
            attempt_count=1,
            started_at=timezone.now(),
            heartbeat_at=timezone.now(),
        )

        result = generate_report_task.apply(
            args=[job.id],
            task_id="duplicate-task",
            throw=True,
        ).get()

        self.assertEqual(result["status"], "skipped")
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.RUNNING)
        self.assertEqual(job.task_id, "active-task")
        self.assertEqual(job.attempt_count, 1)

    def test_completed_job_is_idempotently_skipped(self):
        job = self.make_job(
            status=ReportJob.Status.DONE,
            report_file="already-created.xlsx",
            finished_at=timezone.now(),
        )

        result = generate_report_task.apply(
            args=[job.id],
            task_id="late-duplicate",
            throw=True,
        ).get()

        self.assertEqual(result["status"], "skipped")
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.DONE)
        self.assertEqual(job.report_file, "already-created.xlsx")

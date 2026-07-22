from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from analytics.tasks.cleanup import delete_old_reports
from core.models.tasks import ScheduledTaskRun
from reporting.models.reports import ReportJob
from reporting.services.storage import report_exists, save_report
from users.factories.user_factories import UserFactory


@override_settings(REPORT_RETENTION_DAYS=30)
class ReportCleanupStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def create_expired_report(self):
        report_name = save_report(
            "expired-report.xlsx",
            b"expired report",
        )
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            status=ReportJob.Status.DONE,
            params={},
            finished_at=timezone.now() - timedelta(days=31),
            report_file=report_name,
        )
        return job, report_name

    def test_cleanup_deletes_storage_object_and_job(self):
        job, report_name = self.create_expired_report()

        delete_old_reports.run()

        self.assertFalse(ReportJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(report_exists(report_name))

        run = ScheduledTaskRun.objects.get(task_name="delete_old_reports")
        self.assertEqual(run.status, ScheduledTaskRun.Status.SUCCESS)
        self.assertIn("1 report jobs", run.message)
        self.assertIn("1 report files", run.message)

    @patch(
        "analytics.tasks.cleanup.delete_report",
        side_effect=OSError("storage unavailable"),
    )
    def test_cleanup_keeps_job_when_storage_delete_fails(
        self,
        mock_delete_report,
    ):
        job, report_name = self.create_expired_report()

        delete_old_reports.run()

        self.assertTrue(ReportJob.objects.filter(pk=job.pk).exists())
        self.assertTrue(report_exists(report_name))
        mock_delete_report.assert_called_once_with(report_name)

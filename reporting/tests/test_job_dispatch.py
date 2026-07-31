from unittest.mock import Mock, patch

from django.test import TestCase

from reporting.models.reports import ReportJob
from reporting.services.job_dispatch import enqueue_report_job
from users.factories.user_factories import UserFactory


class ReportJobDispatchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def make_job(self):
        return ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            params={},
        )

    @patch("reporting.services.job_dispatch.task_for_job")
    def test_dispatch_reserves_task_id_before_enqueue(self, mock_task_for_job):
        task = Mock()
        mock_task_for_job.return_value = task
        job = self.make_job()

        self.assertTrue(enqueue_report_job(job.id))

        job.refresh_from_db()
        self.assertTrue(job.task_id)
        self.assertIsNotNone(job.heartbeat_at)
        task.apply_async.assert_called_once_with(
            args=[job.id],
            task_id=job.task_id,
        )

    @patch("reporting.services.job_dispatch.task_for_job")
    def test_second_dispatch_does_not_duplicate_reserved_job(
        self,
        mock_task_for_job,
    ):
        task = Mock()
        mock_task_for_job.return_value = task
        job = self.make_job()

        self.assertTrue(enqueue_report_job(job.id))
        self.assertFalse(enqueue_report_job(job.id))
        task.apply_async.assert_called_once()

    @patch("reporting.services.job_dispatch.task_for_job")
    def test_broker_failure_releases_dispatch_reservation(
        self,
        mock_task_for_job,
    ):
        task = Mock()
        task.apply_async.side_effect = ConnectionError("broker unavailable")
        mock_task_for_job.return_value = task
        job = self.make_job()

        self.assertFalse(enqueue_report_job(job.id))

        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.PENDING)
        self.assertEqual(job.task_id, "")
        self.assertIsNone(job.heartbeat_at)

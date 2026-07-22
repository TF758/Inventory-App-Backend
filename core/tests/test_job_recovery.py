from datetime import timedelta
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.utils import timezone

from core.tasks.job_recovery import recover_stale_report_jobs
from reporting.models.reports import ReportJob
from users.factories.user_factories import UserFactory


@override_settings(
    JOB_STALE_AFTER_SECONDS=60,
    JOB_DISPATCH_GRACE_SECONDS=10,
    JOB_MAX_ATTEMPTS=3,
)
class JobRecoveryTaskTests(TestCase):
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

    @patch("core.tasks.job_recovery.enqueue_report_job", return_value=True)
    def test_stale_running_job_is_requeued(self, mock_enqueue):
        stale_at = timezone.now() - timedelta(minutes=5)
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="lost-worker",
            attempt_count=1,
            started_at=stale_at,
            heartbeat_at=stale_at,
        )

        result = recover_stale_report_jobs.apply(
            task_id="recovery-one",
            throw=True,
        ).get()

        self.assertEqual(result["recovered"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.PENDING)
        self.assertEqual(job.task_id, "")
        mock_enqueue.assert_called_once_with(job.id)

    @patch("core.tasks.job_recovery.enqueue_report_job", return_value=True)
    def test_orphaned_pending_job_is_dispatched(self, mock_enqueue):
        job = self.make_job()
        ReportJob.objects.filter(pk=job.pk).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )

        result = recover_stale_report_jobs.apply(
            task_id="recovery-two",
            throw=True,
        ).get()

        self.assertEqual(result["recovered"], 1)
        mock_enqueue.assert_called_once_with(job.id)


    @patch("core.tasks.job_recovery.enqueue_report_job", return_value=True)
    def test_pre_patch_completed_import_without_workbook_is_requeued(
        self,
        mock_enqueue,
    ):
        job = self.make_job(
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": "equipment",
                "stored_file_name": "already-removed.csv",
            },
            status=ReportJob.Status.DONE,
            result_payload={"summary": {}, "issues": []},
            finished_at=timezone.now() - timedelta(minutes=5),
        )

        result = recover_stale_report_jobs.apply(
            task_id="recovery-old-handoff",
            throw=True,
        ).get()

        self.assertEqual(result["recovered"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.PENDING)
        mock_enqueue.assert_called_once_with(job.id)

    @patch("core.tasks.job_recovery.enqueue_report_job")
    def test_exhausted_import_is_failed_and_upload_is_deleted(
        self,
        mock_enqueue,
    ):
        stored_name = default_storage.save(
            "imports/source/abandoned.csv",
            ContentFile(b"name\nLaptop"),
        )
        stale_at = timezone.now() - timedelta(minutes=5)
        job = self.make_job(
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": "equipment",
                "stored_file_name": stored_name,
            },
            status=ReportJob.Status.RUNNING,
            task_id="lost-import",
            attempt_count=3,
            started_at=stale_at,
            heartbeat_at=stale_at,
        )

        result = recover_stale_report_jobs.apply(
            task_id="recovery-three",
            throw=True,
        ).get()

        self.assertEqual(result["failed"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.FAILED)
        self.assertEqual(job.error, "Import processing failed.")
        self.assertFalse(default_storage.exists(stored_name))
        mock_enqueue.assert_not_called()

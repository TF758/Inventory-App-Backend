from unittest.mock import patch

from celery.exceptions import Retry
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import OperationalError
from django.test import TestCase

from data_import.tasks import run_asset_import_task
from reporting.models.reports import ReportJob
from users.factories.user_factories import UserFactory


class AssetImportTaskTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    @patch("data_import.tasks.enqueue_report_job")
    @patch("data_import.tasks.build_asset_import")
    def test_run_asset_import_task_happy_path(
        self,
        mock_build_import,
        mock_enqueue_report,
    ):

        mock_build_import.return_value = {
            "summary": {"imported_rows": 1}
        }

        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": "equipment",
                "stored_file_name": "test.csv",
            },
        )

        run_asset_import_task(job.id)

        job.refresh_from_db()

        self.assertIsNotNone(job.result_payload)
        self.assertEqual(job.result_payload["summary"]["imported_rows"], 1)

        mock_build_import.assert_called_once()
        mock_enqueue_report.assert_called_once_with(job.id)

    @patch("data_import.tasks.enqueue_report_job")
    @patch("data_import.tasks.build_asset_import")
    def test_completed_import_deletes_stored_upload(
        self,
        mock_build_import,
        mock_enqueue_report,
    ):
        mock_build_import.return_value = {
            "summary": {"imported_rows": 1}
        }
        stored_file_name = default_storage.save(
            "imports/source/task-cleanup.csv",
            ContentFile(b"name\nLaptop"),
        )
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": "equipment",
                "stored_file_name": stored_file_name,
            },
        )

        run_asset_import_task(job.id)

        self.assertFalse(default_storage.exists(stored_file_name))
        mock_enqueue_report.assert_called_once_with(job.id)

    @patch(
        "data_import.tasks.run_asset_import_task.retry",
        side_effect=Retry(),
    )
    @patch("data_import.tasks.build_asset_import")
    def test_transient_import_failure_keeps_lease_and_upload(
        self,
        mock_build_import,
        mock_retry,
    ):
        mock_build_import.side_effect = OperationalError(
            "database temporarily unavailable"
        )
        stored_file_name = default_storage.save(
            "imports/source/retry.csv",
            ContentFile(b"name\nLaptop"),
        )
        self.addCleanup(
            lambda: default_storage.exists(stored_file_name)
            and default_storage.delete(stored_file_name)
        )
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": "equipment",
                "stored_file_name": stored_file_name,
            },
        )

        with self.assertRaises(Retry):
            run_asset_import_task.run(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.RUNNING)
        self.assertTrue(job.task_id)
        self.assertIsNotNone(job.heartbeat_at)
        self.assertEqual(job.attempt_count, 2)
        self.assertTrue(default_storage.exists(stored_file_name))
        mock_retry.assert_called_once()

    @patch(
        "data_import.tasks.run_asset_import_task.retry",
        side_effect=Retry(),
    )
    @patch(
        "data_import.tasks.claim_job",
        side_effect=OperationalError("database temporarily unavailable"),
    )
    def test_transient_claim_failure_is_retried(
        self,
        mock_claim_job,
        mock_retry,
    ):
        with self.assertRaises(Retry):
            run_asset_import_task.run(999999)

        mock_claim_job.assert_called_once()
        mock_retry.assert_called_once()

    @patch("data_import.tasks.build_asset_import")
    def test_import_failure_raises(self, mock_build_import):

        mock_build_import.side_effect = Exception("Import failed")

        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={
                "asset_type": "equipment",
                "stored_file_name": "test.csv",
            },
        )

        with self.assertRaises(Exception):
            run_asset_import_task(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.FAILED)
        self.assertEqual(job.error, "Import processing failed.")
        self.assertEqual(
            job.result_payload["fatal_error"],
            "Import processing failed.",
        )
        self.assertNotIn("Import failed", str(job.result_payload))

    @patch("data_import.tasks.build_asset_import")
    def test_cancelled_import_is_not_started(self, mock_build_import):
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            status=ReportJob.Status.CANCELLED,
            params={
                "asset_type": "equipment",
                "stored_file_name": "test.csv",
            },
        )

        run_asset_import_task(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.CANCELLED)
        mock_build_import.assert_not_called()

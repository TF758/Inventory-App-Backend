from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from unittest.mock import patch
from data_import.tasks import run_asset_import_task
from users.factories.user_factories import UserFactory
from reporting.models.reports import ReportJob



class AssetImportTaskTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    @patch("data_import.tasks.generate_report_task.delay")
    @patch("data_import.tasks.build_asset_import")
    def test_run_asset_import_task_happy_path(
        self,
        mock_build_import,
        mock_generate_report,
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
        mock_generate_report.assert_called_once()


    @patch("data_import.tasks.generate_report_task.delay")
    @patch("data_import.tasks.build_asset_import")
    def test_completed_import_deletes_stored_upload(
        self,
        mock_build_import,
        mock_generate_report,
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
        mock_generate_report.assert_called_once_with(job.id)

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

from django.test import TestCase
from unittest.mock import patch
from data_import.tasks import run_asset_import_task
from db_inventory.factories.user_factories import UserFactory
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
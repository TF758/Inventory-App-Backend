from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from django.urls import reverse

from users.factories.user_factories import AdminUserFactory
from users.models.roles import RoleAssignment
from reporting.models.reports import ReportJob

class AssetImportAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = AdminUserFactory()
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.user,
            role="SITE_ADMIN",
            assigned_by=self.user,
        )
        self.user.active_role = self.site_admin_role
        self.user.save(update_fields=["active_role"])

        self.url = reverse("asset-import")

        self.client.force_authenticate(user=self.user)

    @patch("data_import.views.run_asset_import_task.delay")
    def test_asset_import_happy_path(self, mock_task):

        csv = SimpleUploadedFile(
            "import.csv",
            b"name,brand,model,serial_number,status,room\nLaptop,Dell,XPS,123,OK,R001",
            content_type="text/csv",
        )

        response = self.client.post(
            self.url,
            {
                "asset_type": "equipment",
                "file": csv,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 202)

        job = ReportJob.objects.first()

        self.assertIsNotNone(job)
        self.assertEqual(job.report_type, ReportJob.ReportType.ASSET_IMPORT)

        mock_task.assert_called_once()

    def test_reject_non_csv_file(self):

        file = SimpleUploadedFile(
            "file.txt",
            b"hello",
            content_type="text/plain",
        )

        response = self.client.post(
            self.url,
            {
                "asset_type": "equipment",
                "file": file,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_asset_type(self):

        csv = SimpleUploadedFile(
            "import.csv",
            b"name\nLaptop",
            content_type="text/csv",
        )

        response = self.client.post(
            self.url,
            {
                "asset_type": "invalid",
                "file": csv,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

    def test_file_size_limit(self):

        big_file = SimpleUploadedFile(
            "import.csv",
            b"x" * (6 * 1024 * 1024),
            content_type="text/csv",
        )

        response = self.client.post(
            self.url,
            {
                "asset_type": "equipment",
                "file": big_file,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

    def test_authentication_required(self):

        self.client.force_authenticate(None)

        csv = SimpleUploadedFile(
            "import.csv",
            b"name\nLaptop",
            content_type="text/csv",
        )

        response = self.client.post(
            self.url,
            {
                "asset_type": "equipment",
                "file": csv,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 401)
    def test_cancel_pending_import(self):
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            params={"asset_type": "equipment", "stored_file_name": "test.csv"},
        )

        response = self.client.post(
            reverse("asset-import-cancel", args=[job.public_id])
        )

        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.CANCELLED)
        self.assertIsNotNone(job.finished_at)

    def test_cancel_finished_import_returns_conflict(self):
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            status=ReportJob.Status.DONE,
            params={"asset_type": "equipment", "stored_file_name": "test.csv"},
        )

        response = self.client.post(
            reverse("asset-import-cancel", args=[job.public_id])
        )

        self.assertEqual(response.status_code, 409)
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.DONE)

    def test_failed_import_status_does_not_expose_internal_error(self):
        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.ASSET_IMPORT,
            status=ReportJob.Status.FAILED,
            params={
                "asset_type": "equipment",
                "stored_file_name": "test.csv",
            },
            error="database password appeared in an exception",
            result_payload={
                "fatal_error": "database password appeared in an exception",
            },
        )

        response = self.client.get(
            reverse("asset-import-status", args=[job.public_id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"], "Import processing failed.")
        self.assertEqual(
            response.json()["fatal_error"],
            "Import processing failed.",
        )
        self.assertNotContains(response, "database password")


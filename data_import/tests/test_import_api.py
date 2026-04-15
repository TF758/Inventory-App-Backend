from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from django.urls import reverse

from db_inventory.factories.user_factories import UserFactory
from reporting.models.reports import ReportJob

class AssetImportAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.url = reverse("asset-import")

        self.client.force_authenticate(self.user)

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
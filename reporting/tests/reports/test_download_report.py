from django.test import TestCase
from django.urls import reverse
from django.conf import settings
import uuid
from rest_framework.test import APIClient

from db_inventory.factories.user_factories import UserFactory
from reporting.models.reports import ReportJob



class DownloadReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory()
        cls.other_user = UserFactory()

    def setUp(self):

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------
    # Pending Report
    # -------------------------------------------------

    def test_download_pending_report_returns_202(self):

        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            status=ReportJob.Status.PENDING,
            params={},
        )

        url = reverse("download-report", args=[job.public_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 202)
        self.assertIn("still being generated", response.json()["detail"])

    # -------------------------------------------------
    # Failed Report
    # -------------------------------------------------

    def test_download_failed_report_returns_error(self):

        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            status=ReportJob.Status.FAILED,
            params={},
            error="Generation failed",
        )

        url = reverse("download-report", args=[job.public_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "Generation failed")

    # -------------------------------------------------
    # File Missing
    # -------------------------------------------------

    def test_download_missing_file_returns_404(self):

        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            status=ReportJob.Status.DONE,
            params={},
            report_file="missing_file.xlsx",
        )

        url = reverse("download-report", args=[job.public_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    # -------------------------------------------------
    # Successful Download
    # -------------------------------------------------

    def test_download_success(self):

        filename = f"test_report_{uuid.uuid4().hex}.xlsx"
        file_path = settings.REPORTS_DIR / filename

        file_path.write_bytes(b"test report content")

        job = ReportJob.objects.create(
            user=self.user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            status=ReportJob.Status.DONE,
            params={},
            report_file=filename,
        )

        url = reverse("download-report", args=[job.public_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="{filename}"'
        )

        # release file lock
        b"".join(response.streaming_content)

        file_path.unlink()
        # -------------------------------------------------
    # Ownership Protection
    # -------------------------------------------------

    def test_user_cannot_download_other_users_report(self):

        job = ReportJob.objects.create(
            user=self.other_user,
            report_type=ReportJob.ReportType.USER_SUMMARY,
            status=ReportJob.Status.DONE,
            params={},
        )

        url = reverse("download-report", args=[job.public_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
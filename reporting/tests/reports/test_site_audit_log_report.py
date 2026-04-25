from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models.audit import AuditLog
from core.factories.audit_factories import AuditLogFactory
from users.factories.user_factories import UserFactory
from sites.factories.site_factories import DepartmentFactory, LocationFactory, RoomFactory
from reporting.services.site_reports import build_site_audit_log_report
from reporting.utils.report_adapters.site_reports import site_audit_log_to_workbook_spec






class SiteAuditLogReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.department = DepartmentFactory(name="IT")
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

    def _meta(self):
        return {
            "report_name": "Site Audit Log Report",
            "generated_at": timezone.now(),
            "generated_by": "tester",
            "site_type": "department",
            "site_id": "DEP123",
            "site_name": "IT",
            "audit_period_days": 30,
        }

    # -------------------------------------------------
    # Builder Tests
    # -------------------------------------------------

    def test_builder_returns_structure(self):
        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertIn("meta", result)
        self.assertIn("data", result)
        self.assertIn("summary", result["data"])
        self.assertIn("tables", result["data"])

    def test_builder_filters_by_site_scope(self):
        AuditLog.objects.bulk_create(
            [
                AuditLogFactory(
                    department=self.department,
                    department_name=self.department.name,
                    event_type="login",
                ),
                AuditLogFactory(
                    department=None,
                    event_type="login",
                ),
            ]
        )

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertEqual(
            len(result["data"]["tables"]["Audit Logs"]),
            1,
        )

    def test_builder_respects_audit_period(self):
        now = timezone.now()

        AuditLog.objects.bulk_create(
            [
                AuditLogFactory(
                    department=self.department,
                    department_name=self.department.name,
                    event_type="login",
                    created_at=now - timedelta(days=5),
                ),
                AuditLogFactory(
                    department=self.department,
                    department_name=self.department.name,
                    event_type="login",
                    created_at=now - timedelta(days=60),
                ),
            ]
        )

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertEqual(
            len(result["data"]["tables"]["Audit Logs"]),
            1,
        )

    def test_builder_formats_event_labels(self):
        AuditLog.objects.bulk_create(
            [
                AuditLogFactory(
                    department=self.department,
                    department_name=self.department.name,
                    event_type="login",
                ),
            ]
        )

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        log = result["data"]["tables"]["Audit Logs"][0]

        self.assertEqual(log["action"], "Login")

    def test_builder_handles_no_logs(self):
        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertEqual(
            result["data"]["tables"]["Audit Logs"],
            [],
        )

    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_report_info_sheet(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "log_count": 0,
                    "audit_period_days": 30,
                },
                "tables": {
                    "Audit Logs": [],
                },
            },
        }

        spec = site_audit_log_to_workbook_spec(payload)

        self.assertIn("Report Info", spec)

    def test_renderer_creates_audit_log_sheet(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "log_count": 1,
                    "audit_period_days": 30,
                },
                "tables": {
                    "Audit Logs": [
                        {
                            "date": "2024-01-01",
                            "time": "10:00:00",
                            "action": "Login",
                            "performed_by": "user@example.com",
                            "affected_item_type": None,
                            "affected_item": None,
                            "department": "IT",
                            "location": None,
                            "room": None,
                            "source_ip": "127.0.0.1",
                            "audit_reference": "LOG001",
                        }
                    ],
                },
            },
        }

        spec = site_audit_log_to_workbook_spec(payload)

        self.assertIn("Audit Logs", spec)

    def test_renderer_handles_empty_logs(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "log_count": 0,
                    "audit_period_days": 30,
                },
                "tables": {
                    "Audit Logs": [],
                },
            },
        }

        spec = site_audit_log_to_workbook_spec(payload)

        self.assertIn("Audit Logs", spec)
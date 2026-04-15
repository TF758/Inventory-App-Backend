from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from db_inventory.models.audit import AuditLog
from db_inventory.factories.audit_factories import AuditLogFactory
from db_inventory.factories.site_factories import ( DepartmentFactory, LocationFactory, RoomFactory, )
from db_inventory.factories.user_factories import UserFactory
from reporting.services.site_reports import build_site_audit_log_report
from reporting.utils.report_adapters.site_reports import site_audit_log_to_workbook_spec




class SiteAuditLogReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory()

        cls.department = DepartmentFactory(name="IT")
        cls.location = LocationFactory(department=cls.department)
        cls.room = RoomFactory(location=cls.location)

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

        self.assertIn("logs", result)


    def test_builder_filters_by_site_scope(self):

        AuditLog.objects.bulk_create([
            AuditLogFactory(
                department=self.department,
                department_name=self.department.name,
                event_type="login",
            ),
            AuditLogFactory(
                department=None,
                event_type="login",
            ),
        ])

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertEqual(len(result["logs"]), 1)


    def test_builder_respects_audit_period(self):

        now = timezone.now()

        AuditLog.objects.bulk_create([
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
        ])

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertEqual(len(result["logs"]), 1)


    def test_builder_formats_event_labels(self):

        AuditLog.objects.bulk_create([
            AuditLogFactory(
                department=self.department,
                department_name=self.department.name,
                event_type="login",
            ),
        ])

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        log = result["logs"][0]

        self.assertEqual(log["action"], "Login")


    def test_builder_handles_no_logs(self):

        result = build_site_audit_log_report(
            site={
                "siteType": "department",
                "siteId": self.department.public_id,
            },
            audit_period_days=30,
        )

        self.assertEqual(result["logs"], [])


    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_report_info_sheet(self):

        payload = {
            "meta": {
                "generated_at": timezone.now(),
                "generated_by": "tester",
                "site_type": "department",
                "site_id": "DEP123",
                "site_name": "IT",
                "audit_period_days": 30,
            },
            "data": {
                "logs": []
            },
        }

        spec = site_audit_log_to_workbook_spec(payload)

        self.assertIn("Report Info", spec)


    def test_renderer_creates_audit_log_sheet(self):

        payload = {
            "meta": {},
            "data": {
                "logs": [
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
                ]
            },
        }

        spec = site_audit_log_to_workbook_spec(payload)

        self.assertIn("Audit Logs", spec)
        self.assertEqual(spec["Audit Logs"]["headers"][0], "date")


    def test_renderer_handles_empty_logs(self):

        payload = {
            "meta": {},
            "data": {
                "logs": []
            },
        }

        spec = site_audit_log_to_workbook_spec(payload)

        self.assertEqual(
            spec["Audit Logs"]["rows"][0][0],
            "No audit log entries were found for the selected site and time period.",
        )
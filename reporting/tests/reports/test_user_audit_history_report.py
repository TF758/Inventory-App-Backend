from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from db_inventory.models.audit import AuditLog
from db_inventory.factories.audit_factories import AuditLogFactory
from db_inventory.factories.user_factories import UserFactory
from reporting.services.user_summary import build_user_audit_history_report
from reporting.utils.report_adapters.user_summary import user_audit_history_to_workbook_spec




class UserAuditHistoryReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory(
            email="user@example.com",
            fname="John",
            lname="Doe",
        )

        cls.other_user = UserFactory()

    # -------------------------------------------------
    # Builder Tests
    # -------------------------------------------------

    def test_builder_raises_if_user_not_found(self):

        with self.assertRaises(ValueError):

            build_user_audit_history_report(
                user_identifier="nonexistent@example.com",
            )


    def test_builder_returns_basic_structure(self):

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        self.assertIn("report_info", result)
        self.assertIn("audit_stats", result)
        self.assertIn("history_rows", result)


    def test_builder_aggregates_event_stats(self):

        AuditLog.objects.bulk_create([
            AuditLogFactory(user=self.user, event_type="login"),
            AuditLogFactory(user=self.user, event_type="login"),
            AuditLogFactory(user=self.user, event_type="logout"),
        ])

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        stats = result["audit_stats"]

        self.assertEqual(stats["login"], 2)
        self.assertEqual(stats["logout"], 1)


    def test_builder_filters_by_date_range(self):

        now = timezone.now()

        AuditLog.objects.bulk_create([
            AuditLogFactory(
                user=self.user,
                event_type="login",
                created_at=now - timedelta(days=5),
            ),
            AuditLogFactory(
                user=self.user,
                event_type="logout",
                created_at=now - timedelta(days=40),
            ),
        ])

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
            start_date=now - timedelta(days=30),
        )

        stats = result["audit_stats"]

        self.assertEqual(stats["login"], 1)
        self.assertNotIn("logout", stats)


    def test_builder_ignores_other_users(self):

        AuditLog.objects.bulk_create([
            AuditLogFactory(user=self.user, event_type="login"),
            AuditLogFactory(user=self.other_user, event_type="login"),
        ])

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        stats = result["audit_stats"]

        self.assertEqual(stats["login"], 1)


    def test_builder_handles_user_with_no_audit_logs(self):

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        self.assertEqual(result["audit_stats"], {})
        self.assertEqual(list(result["history_rows"]), [])

    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_expected_sheets(self):

        payload = {
            "meta": {},
            "data": {
                "report_info": {},
                "audit_stats": {},
                "history_rows": [],
            },
        }

        spec = user_audit_history_to_workbook_spec(payload)

        self.assertIn("Report Info", spec)
        self.assertIn("Audit Stats", spec)
        self.assertIn("History", spec)


    def test_renderer_handles_empty_payload_sections(self):

        payload = {
            "meta": {},
            "data": {},
        }

        spec = user_audit_history_to_workbook_spec(payload)

        self.assertEqual(
            spec["Audit Stats"]["rows"][0][0],
            "No audit events recorded for this user.",
        )


    def test_renderer_formats_history_rows(self):

        payload = {
            "meta": {},
            "data": {
                "report_info": {},
                "audit_stats": {},
                "history_rows": [
                    [
                        timezone.now(),
                        "login",
                        "User logged in",
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        "127.0.0.1",
                        "test-agent",
                    ]
                ],
            },
        }

        spec = user_audit_history_to_workbook_spec(payload)

        rows = spec["History"]["rows"]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "login")
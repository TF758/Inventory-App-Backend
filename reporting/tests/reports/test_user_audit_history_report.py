from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models.audit import AuditLog
from core.factories.audit_factories import AuditLogFactory
from users.factories.user_factories import UserFactory
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

    def _meta(self):
        return {
            "report_name": "User Audit History Report",
            "generated_at": timezone.now(),
            "generated_by": "tester",
            "user_public_id": self.user.public_id,
            "user_email": self.user.email,
            "user_full_name": self.user.get_full_name(),
            "start_date": None,
            "end_date": timezone.now(),
        }

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

        self.assertIn("meta", result)
        self.assertIn("data", result)
        self.assertIn("summary", result["data"])
        self.assertIn("history_rows", result["data"])

    def test_builder_aggregates_event_stats(self):
        AuditLog.objects.bulk_create(
            [
                AuditLogFactory(
                    user=self.user,
                    event_type="login",
                ),
                AuditLogFactory(
                    user=self.user,
                    event_type="login",
                ),
                AuditLogFactory(
                    user=self.user,
                    event_type="logout",
                ),
            ]
        )

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        self.assertEqual(
            result["data"]["summary"]["total_events"],
            3,
        )

    def test_builder_filters_by_date_range(self):
        now = timezone.now()

        AuditLog.objects.bulk_create(
            [
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
            ]
        )

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
            start_date=now - timedelta(days=30),
        )

        self.assertEqual(
            result["data"]["summary"]["total_events"],
            1,
        )

    def test_builder_ignores_other_users(self):
        AuditLog.objects.bulk_create(
            [
                AuditLogFactory(
                    user=self.user,
                    event_type="login",
                ),
                AuditLogFactory(
                    user=self.other_user,
                    event_type="login",
                ),
            ]
        )

        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        self.assertEqual(
            result["data"]["summary"]["total_events"],
            1,
        )

    def test_builder_handles_user_with_no_audit_logs(self):
        result = build_user_audit_history_report(
            user_identifier=self.user.email,
        )

        self.assertEqual(
            result["data"]["summary"]["total_events"],
            0,
        )

        self.assertEqual(
            list(result["data"]["history_rows"]),
            [],
        )

    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_expected_sheets(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "total_events": 0,
                },
                "history_rows": [],
            },
        }

        spec = user_audit_history_to_workbook_spec(payload)

        self.assertIn("Report Info", spec)
        self.assertIn("Audit Stats", spec)
        self.assertIn("History", spec)

    def test_renderer_handles_empty_payload_sections(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {},
                "history_rows": [],
            },
        }

        spec = user_audit_history_to_workbook_spec(payload)

        self.assertEqual(
            spec["Audit Stats"]["rows"][0][0],
            "No audit events recorded for this user.",
        )

    def test_renderer_formats_history_rows(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary": {
                    "total_events": 1,
                },
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
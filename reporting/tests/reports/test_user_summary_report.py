

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from db_inventory.factories.audit_factories import AuditLogFactory
from db_inventory.factories.security_factories import PasswordResetEventFactory
from db_inventory.factories.session_factories import UserSessionFactory
from db_inventory.factories.user_factories import RoleAssignmentFactory, UserFactory
from db_inventory.models.audit import AuditLog
from db_inventory.factories.site_factories import DepartmentFactory
from reporting.services.user_summary import build_user_summary_report
from reporting.utils.report_adapters.user_summary import user_summary_to_workbook_spec


class UserSummaryReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory(
            email="user@example.com",
            fname="John",
            lname="Doe",
        )

        cls.other_user = UserFactory()
    def test_login_stats_counts_sessions_correctly(self):

        UserSessionFactory.create_batch(
            2,
            user=self.user,
            status="active",
        )

        UserSessionFactory(user=self.user, status="revoked")
        UserSessionFactory(user=self.user, status="expired")

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["loginStats"],
        )

        stats = result["loginStats"]

        self.assertEqual(stats["active_sessions"], 2)
        self.assertEqual(stats["revoked_sessions"], 1)
        self.assertEqual(stats["expired_sessions"], 1)

    # -------------------------
    # Builder tests
    # -------------------------

    def test_builder_returns_requested_sections_only(self):

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["demographics"],
            generated_by=None,
        )

        self.assertIn("demographics", result)
        self.assertNotIn("loginStats", result)
        self.assertNotIn("auditSummary", result)


    def test_builder_raises_if_user_not_found(self):

        with self.assertRaises(ValueError):

            build_user_summary_report(
                user_identifier="nonexistent@example.com",
                sections=["demographics"],
                generated_by=None,
            )


    def test_login_stats_counts_sessions_correctly(self):

        UserSessionFactory(user=self.user, status="active")
        UserSessionFactory(user=self.user, status="revoked")
        UserSessionFactory(user=self.user, status="expired")

        UserSessionFactory(
            user=self.user,
            status="active",
            last_used_at=timezone.now(),
        )

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["loginStats"],
            generated_by=None,
        )

        stats = result["loginStats"]

        self.assertEqual(stats["active_sessions"], 2)
        self.assertEqual(stats["revoked_sessions"], 1)
        self.assertEqual(stats["expired_sessions"], 1)


    def test_login_frequency_last_30_days(self):

        UserSessionFactory(
            user=self.user,
            last_used_at=timezone.now() - timedelta(days=10),
        )

        UserSessionFactory(
            user=self.user,
            last_used_at=timezone.now() - timedelta(days=40),
        )

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["loginStats"],
            generated_by=None,
        )

        stats = result["loginStats"]

        self.assertEqual(stats["login_frequency_last_30_days"], 1)


    def test_audit_summary_aggregates_events(self):

        AuditLog.objects.bulk_create([
            AuditLogFactory(user=self.user, event_type="login"),
            AuditLogFactory(user=self.user, event_type="login"),
            AuditLogFactory(user=self.user, event_type="logout"),
        ])

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["auditSummary"],
            generated_by=None,
        )

        audit = result["auditSummary"]

        self.assertEqual(audit["total"], 3)
        self.assertEqual(audit["events"]["login"], 2)
        self.assertEqual(audit["events"]["logout"], 1)


    def test_role_summary_scope_resolution(self):

        dept = DepartmentFactory(name="IT")

        RoleAssignmentFactory(
            user=self.user,
            role="DEPARTMENT_ADMIN",
            department=dept,
        )

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["roleSummary"],
            generated_by=None,
        )

        roles = result["roleSummary"]

        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0]["scope"], "IT")


    def test_password_event_counts(self):

        PasswordResetEventFactory(user=self.user, is_active=True)
        PasswordResetEventFactory(user=self.user, is_active=False)

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["passwordevents"],
            generated_by=None,
        )

        pw = result["passwordevents"]

        self.assertEqual(pw["total_password_reset_events"], 2)
        self.assertEqual(pw["active_reset_tokens"], 1)


    # -------------------------
    # Renderer tests
    # -------------------------

    def test_renderer_generates_expected_sheets(self):

        payload = {
            "meta": {},
            "data": {
                "demographics": {
                    "full_name": "John Doe",
                    "email": "user@example.com",
                }
            },
        }

        spec = user_summary_to_workbook_spec(payload)

        self.assertIn("Demographics", spec)
        self.assertIn("Login Stats", spec)
        self.assertIn("Audit Summary", spec)
        self.assertIn("Role Summary", spec)
        self.assertIn("Password Events", spec)


    def test_renderer_handles_missing_sections_gracefully(self):

        payload = {
            "meta": {},
            "data": {},
        }

        spec = user_summary_to_workbook_spec(payload)

        self.assertEqual(
            spec["Login Stats"]["rows"][0][0],
            "No login statistics available.",
        )


    def test_renderer_formats_demographic_keys(self):

        payload = {
            "meta": {},
            "data": {
                "demographics": {
                    "full_name": "John Doe",
                }
            },
        }

        spec = user_summary_to_workbook_spec(payload)

        header, value = spec["Demographics"]["rows"][0]

        self.assertEqual(header, "Full Name")
        self.assertEqual(value, "John Doe")
    

    def test_builder_handles_user_with_no_activity(self):

        result = build_user_summary_report(
            user_identifier=self.user.email,
            sections=["loginStats", "auditSummary"],
        )

        self.assertEqual(result["loginStats"]["active_sessions"], 0)
        self.assertEqual(result["auditSummary"]["total"], 0)
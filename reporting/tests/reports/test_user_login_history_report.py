from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from core.models.audit import AuditLog
from core.factories.audit_factories import AuditLogFactory
from core.factories.session_factories import UserSessionFactory
from core.models.sessions import UserSession
from users.factories.user_factories import UserFactory
from reporting.services.user_summary import build_user_login_history_report
from reporting.utils.report_adapters.user_summary import user_login_history_to_workbook_spec



class UserLoginHistoryReportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            email="user@example.com",
            fname="John",
            lname="Doe",
        )

        cls.other_user = UserFactory()

        cls.start = date.today() - timedelta(days=30)
        cls.end = date.today()

        cls.now = timezone.now() - timedelta(days=1)

    def _meta(self):
        return {
            "report_name": "User Login History Report",
            "generated_at": timezone.now(),
            "generated_by": "tester",
            "user_public_id": self.user.public_id,
            "user_email": self.user.email,
            "user_full_name": self.user.get_full_name(),
            "start_date": self.start,
            "end_date": self.end,
        }

    # -------------------------------------------------
    # Builder Tests
    # -------------------------------------------------

    def test_builder_raises_if_user_not_found(self):
        with self.assertRaises(ValueError):
            build_user_login_history_report(
                user_identifier="invalid@example.com",
                start_date=self.start,
                end_date=self.end,
            )

    def test_builder_returns_structure(self):
        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        self.assertIn("meta", result)
        self.assertIn("data", result)
        self.assertIn("summary_stats", result["data"])

    def test_builder_counts_login_events(self):
        AuditLog.objects.bulk_create([
            AuditLogFactory(
                user=self.user,
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
            AuditLogFactory(
                user=self.user,
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
            AuditLogFactory(
                user=self.user,
                event_type=AuditLog.Events.LOGOUT,
                created_at=self.now,
            ),
        ])

        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        summary = result["data"]["summary_stats"]

        self.assertEqual(summary["total_logins"], 2)
        self.assertEqual(summary["total_logouts"], 1)

    def test_builder_calculates_login_success_ratio(self):
        AuditLog.objects.bulk_create([
            AuditLogFactory(
                user=self.user,
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
            AuditLogFactory(
                user=self.user,
                event_type=AuditLog.Events.LOGIN_FAILED,
                created_at=self.now,
            ),
        ])

        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        summary = result["data"]["summary_stats"]

        self.assertEqual(
            summary["login_success_ratio_percent"],
            50.0,
        )

    def test_builder_tracks_unique_ips(self):
        AuditLog.objects.bulk_create([
            AuditLogFactory(
                user=self.user,
                ip_address="1.1.1.1",
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
            AuditLogFactory(
                user=self.user,
                ip_address="2.2.2.2",
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
        ])

        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        summary = result["data"]["summary_stats"]

        self.assertEqual(summary["unique_ips"], 2)

    def test_builder_session_stats(self):
        sessions = UserSessionFactory.create_batch(
            2,
            user=self.user,
            status=UserSession.Status.ACTIVE,
        )

        revoked = UserSessionFactory(
            user=self.user,
            status=UserSession.Status.REVOKED,
        )

        expired = UserSessionFactory(
            user=self.user,
            status=UserSession.Status.EXPIRED,
        )

        for s in sessions + [revoked, expired]:
            s.created_at = self.now
            s.save(update_fields=["created_at"])

        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        session_stats = result["data"]["session_stats"]

        self.assertEqual(session_stats["total_sessions"], 4)
        self.assertEqual(session_stats["active_sessions"], 2)
        self.assertEqual(session_stats["revoked_sessions"], 1)
        self.assertEqual(session_stats["expired_sessions"], 1)

    def test_builder_filters_other_users(self):
        AuditLog.objects.bulk_create([
            AuditLogFactory(
                user=self.user,
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
            AuditLogFactory(
                user=self.other_user,
                event_type=AuditLog.Events.LOGIN,
                created_at=self.now,
            ),
        ])

        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        summary = result["data"]["summary_stats"]

        self.assertEqual(summary["total_logins"], 1)

    def test_builder_handles_no_activity(self):
        result = build_user_login_history_report(
            user_identifier=self.user.email,
            start_date=self.start,
            end_date=self.end,
        )

        summary = result["data"]["summary_stats"]

        self.assertEqual(summary["total_logins"], 0)
        self.assertEqual(summary["failed_logins"], 0)

    # -------------------------------------------------
    # Renderer Tests
    # -------------------------------------------------

    def test_renderer_creates_expected_sheets(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary_stats": {},
                "session_stats": {},
                "login_history": [],
                "ip_breakdown": [],
                "device_breakdown": [],
                "login_timeline": [],
            },
        }

        spec = user_login_history_to_workbook_spec(payload)

        self.assertIn("Summary", spec)
        self.assertIn("Session Stats", spec)
        self.assertIn("Login History", spec)
        self.assertIn("IP Breakdown", spec)
        self.assertIn("Device Breakdown", spec)
        self.assertIn("Login Timeline", spec)

    def test_renderer_login_history_rows(self):
        payload = {
            "meta": self._meta(),
            "data": {
                "summary_stats": {},
                "session_stats": {},
                "login_history": [
                    {
                        "timestamp": timezone.now(),
                        "event_type": "login",
                        "description": "User login",
                        "ip_address": "127.0.0.1",
                        "user_agent": "browser",
                        "department": None,
                        "location": None,
                        "room": None,
                    }
                ],
                "ip_breakdown": [],
                "device_breakdown": [],
                "login_timeline": [],
            },
        }

        spec = user_login_history_to_workbook_spec(payload)

        rows = spec["Login History"]["rows"]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "login")
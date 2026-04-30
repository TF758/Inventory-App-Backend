from django.test import TestCase
from django.utils import timezone
from analytics.tasks import generate_daily_auth_metrics
from analytics.models.metrics import DailyAuthMetrics
from core.models.audit import AuditLog
from core.models.sessions import UserSession
from core.models.security import PasswordResetEvent
from users.factories.user_factories import UserFactory

import uuid

def simulate_session_revoke(self, user):
    AuditLog.objects.create(
        event_type=AuditLog.Events.SESSION_REVOKED,
        user=user,
        user_public_id=str(user.public_id),
        user_email=user.email,
    )



class TestDailyAuthMetrics(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.now = timezone.now()
        cls.today = timezone.localdate()

    # -------------------------
    # Helpers
    # -------------------------
    def simulate_login(self, user, now=None):
        now = now or self.now

        UserSession.objects.create(
            user=user,
            refresh_token_hash=str(uuid.uuid4()),
            status=UserSession.Status.ACTIVE,
            expires_at=now,
            absolute_expires_at=now,
        )

        AuditLog.objects.create(
            event_type=AuditLog.Events.LOGIN,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
        )

    def simulate_failed_login(self):
        AuditLog.objects.create( event_type=AuditLog.Events.LOGIN_FAILED )

    def simulate_session_revoke(self, user):
        AuditLog.objects.create(
            event_type=AuditLog.Events.SESSION_REVOKED,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
        )

    def simulate_password_reset_requested(self, user):
        AuditLog.objects.create(
            event_type=AuditLog.Events.PASSWORD_RESET_REQUESTED,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
        )

    def simulate_password_reset_completed(self, user):
        AuditLog.objects.create(
            event_type=AuditLog.Events.PASSWORD_RESET_COMPLETED,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
        )


    # -------------------------
    # Core aggregation tests
    # -------------------------
    def test_basic_login_aggregation(self):
        AuditLog.objects.create(event_type=AuditLog.Events.LOGIN, user=self.user1)
        AuditLog.objects.create(event_type=AuditLog.Events.LOGIN, user=self.user2)
        AuditLog.objects.create(event_type=AuditLog.Events.LOGIN, user=self.user1)

        AuditLog.objects.create(event_type=AuditLog.Events.LOGIN_FAILED)

        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.total_logins, 3)
        self.assertEqual(metrics.unique_users_logged_in, 2)
        self.assertEqual(metrics.failed_logins, 1)

    def test_session_metrics(self):
        user = UserFactory()

        # active sessions
        UserSession.objects.create(
            user=user,
            refresh_token_hash="a",
            status=UserSession.Status.ACTIVE,
            expires_at=self.now,
            absolute_expires_at=self.now
        )
        UserSession.objects.create(
            user=user,
            refresh_token_hash="b",
            status=UserSession.Status.ACTIVE,
            expires_at=self.now,
            absolute_expires_at=self.now
        )

        self.simulate_session_revoke(user)

        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.active_sessions, 2)
        self.assertEqual(metrics.revoked_sessions, 1)
        self.assertEqual(metrics.users_multiple_active_sessions, 1)
        self.assertEqual(metrics.users_with_revoked_sessions, 1)

    def test_snapshot_created_once(self):
        generate_daily_auth_metrics()
        generate_daily_auth_metrics()

        self.assertEqual(DailyAuthMetrics.objects.count(), 1)

    def test_only_counts_today(self):
        yesterday = timezone.now() - timezone.timedelta(days=1)

        AuditLog.objects.create(
            event_type=AuditLog.Events.LOGIN,
            created_at=yesterday
        )

        generate_daily_auth_metrics()
        metrics = DailyAuthMetrics.objects.first()
        self.assertEqual(metrics.total_logins, 0)

    # -------------------------
    # Simulation tests
    # -------------------------
    def test_simulated_user_activity(self):
        users = UserFactory.create_batch(5)

        for user in users:
            self.simulate_login(user)
            self.simulate_login(user)

        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.total_logins, 10)
        self.assertEqual(metrics.unique_users_logged_in, 5)
        self.assertEqual(metrics.users_multiple_active_sessions, 5)



    def test_simulated_cross_day_activity(self):
        yesterday = self.now - timezone.timedelta(days=1)

        AuditLog.objects.create(
            event_type=AuditLog.Events.LOGIN,
            user=self.user1,
            created_at=yesterday
        )

        self.simulate_login(self.user2)

        generate_daily_auth_metrics()
        metrics = DailyAuthMetrics.objects.first()
        self.assertEqual(metrics.total_logins, 1)

    # -------------------------
    # Date correctness
    # -------------------------
    def test_failed_logins_are_scoped_to_day(self):
        yesterday = self.now - timezone.timedelta(days=1)

        AuditLog.objects.create( event_type=AuditLog.Events.LOGIN_FAILED, created_at=yesterday )
        AuditLog.objects.create( event_type=AuditLog.Events.LOGIN_FAILED, created_at=yesterday )

        self.simulate_failed_login()
        self.simulate_failed_login()

        generate_daily_auth_metrics()
        metrics = DailyAuthMetrics.objects.first()
        self.assertEqual(metrics.failed_logins, 2)


    def test_sessions_should_be_scoped_to_day(self):
        yesterday = self.now - timezone.timedelta(days=1)

        UserSession.objects.create(
            user=self.user1,
            refresh_token_hash=str(uuid.uuid4()),
            status=UserSession.Status.ACTIVE,
            created_at=yesterday,
            expires_at=yesterday + timezone.timedelta(hours=2),
            absolute_expires_at=yesterday + timezone.timedelta(hours=3),
        )

        self.simulate_login(self.user2)

        generate_daily_auth_metrics()
        metrics = DailyAuthMetrics.objects.first()
        self.assertEqual(metrics.active_sessions, 1)
    
    def test_session_revoked_event_count(self):
        self.simulate_session_revoke(self.user1)
        self.simulate_session_revoke(self.user2)

        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.revoked_sessions, 2)
        self.assertEqual(metrics.users_with_revoked_sessions, 2)
    
    def test_session_revoked_scoped_to_day(self):
        yesterday = self.now - timezone.timedelta(days=1)

        AuditLog.objects.create(
            event_type=AuditLog.Events.SESSION_REVOKED,
            user=self.user1,
            created_at=yesterday
        )

        self.simulate_session_revoke(self.user2)
        generate_daily_auth_metrics()
        metrics = DailyAuthMetrics.objects.first()
        self.assertEqual(metrics.revoked_sessions, 1)
    

    def simulate_session_expired(self, user):
        AuditLog.objects.create(
            event_type=AuditLog.Events.SESSION_EXPIRED,
            user=user,
            user_public_id=str(user.public_id),
            user_email=user.email,
        )

    def test_session_expired_event_count(self):
        self.simulate_session_expired(self.user1)
        self.simulate_session_expired(self.user2)

        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.expired_sessions, 2)
    

    def test_password_reset_metrics(self):
        self.simulate_password_reset_requested(self.user1)
        self.simulate_password_reset_requested(self.user2)

        self.simulate_password_reset_completed(self.user1)

        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.password_resets_started, 2)
        self.assertEqual(metrics.password_resets_completed, 1)
    

    def test_password_reset_scoped_to_day(self):
        yesterday = self.now - timezone.timedelta(days=1)

        AuditLog.objects.create(
            event_type=AuditLog.Events.PASSWORD_RESET_REQUESTED,
            user=self.user1, created_at=yesterday )

        self.simulate_password_reset_requested(self.user2)
        generate_daily_auth_metrics()
        metrics = DailyAuthMetrics.objects.first()
        self.assertEqual(metrics.password_resets_started, 1)
    

    def test_active_and_expired_password_resets(self):
        PasswordResetEvent.objects.create(
            user=self.user1,
            token="active", expires_at=self.now + timezone.timedelta(hours=1), )

        PasswordResetEvent.objects.create(
            user=self.user1,
            token="expired", expires_at=self.now - timezone.timedelta(hours=1), )
        
        generate_daily_auth_metrics()

        metrics = DailyAuthMetrics.objects.first()

        self.assertEqual(metrics.active_password_resets, 1)
        self.assertEqual(metrics.expired_password_resets, 1)
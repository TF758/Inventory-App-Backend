from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework.exceptions import ( AuthenticationFailed, )
from rest_framework import status
from django.urls import reverse
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken
from core.models.security import SecuritySettings
from core.models.sessions import UserSession
from core.services.security.login_failures import register_failed_login, reset_failed_logins, validate_user_not_locked
from users.factories.user_factories import UserFactory
class SessionSecurityTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.login_url = reverse( "login", )
        cls.refresh_url = reverse( "session_refresh", )

        cls.user = UserFactory( is_active=True, password="StrongPass123!", )

    def setUp(self):

        self.client = APIClient()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _login(self, client=None):

        client = client or self.client

        return client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": "StrongPass123!",
            },
            format="json",
        )

    # --------------------------------------------------
    # Session security tests
    # --------------------------------------------------

    def test_login_revokes_oldest_session_when_session_limit_reached(
        self,
    ):

        SecuritySettings.objects.create( max_concurrent_sessions=2, )

        self._login()
        self._login()
        self._login()

        sessions = UserSession.objects.filter( user=self.user, )
        active_sessions = sessions.filter( status=UserSession.Status.ACTIVE, )
        revoked_sessions = sessions.filter( status=UserSession.Status.REVOKED, )

        self.assertEqual( active_sessions.count(), 2, )

        self.assertEqual(
            revoked_sessions.count(),
            1,
        )

        oldest = sessions.order_by(
            "created_at",
        ).first()

        self.assertEqual(
            oldest.status,
            UserSession.Status.REVOKED,
        )

    def test_login_ignores_existing_refresh_cookie(
        self,
    ):

        self.client.cookies[
            "refresh"
        ] = (
            "attacker-controlled-cookie"
        )

        response = self._login()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        new_cookie = response.cookies[
            "refresh"
        ].value

        self.assertNotEqual(
            new_cookie,
            "attacker-controlled-cookie",
        )

        sessions = UserSession.objects.filter(
            user=self.user,
        )

        self.assertEqual(
            sessions.count(),
            1,
        )

    def test_refresh_tokens_are_unique_and_secure(
        self,
    ):

        resp1 = self._login()

        token1 = resp1.cookies[
            "refresh"
        ].value

        resp2 = self._login()

        token2 = resp2.cookies[
            "refresh"
        ].value

        self.assertNotEqual( token1, token2, )

        # Ensure token entropy/length
        self.assertGreaterEqual(
            len(token1),
            40,
        )

        self.assertGreaterEqual(
            len(token2),
            40,
        )

    def test_refresh_token_cannot_be_used_by_another_user(
        self,
    ):

        # -----------------------------------------
        # Login user A
        # -----------------------------------------

        resp_a = self._login()

        refresh_token = resp_a.cookies[
            "refresh"
        ].value

        # -----------------------------------------
        # Create/login user B
        # -----------------------------------------

        user_b = UserFactory(
            is_active=True,
            password="StrongPass123!",
        )

        client_b = APIClient()

        login_b = client_b.post(
            self.login_url,
            {
                "email": user_b.email,
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(
            login_b.status_code,
            status.HTTP_200_OK,
        )

        # -----------------------------------------
        # Attempt refresh hijack
        # -----------------------------------------

        client_b.cookies[
            "refresh"
        ] = refresh_token

        response = client_b.post( self.refresh_url, )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        access_token = response.json()[ "access" ]
        payload = AccessToken( access_token, )

        session_id = payload[
            "session_id"
        ]

        session = UserSession.objects.get(
            id=session_id,
        )

        # Must still belong to user A
        self.assertEqual(
            session.user_id,
            self.user.id,
        )

class LoginFailureServiceTests(TestCase):

    # --------------------------------------------------
    # Temporary lockout
    # --------------------------------------------------

    def test_failed_logins_trigger_temp_lock(
        self,
    ):

        policy = SecuritySettings.objects.create(
            enable_account_lockout=True,
            lockout_attempts=3,
            lockout_duration_minutes=15,
            permanent_lock_threshold=10,
        )

        user = UserFactory()

        for _ in range(3):

            register_failed_login(
                user=user,
                policy=policy,
            )

        user.refresh_from_db()

        self.assertIsNotNone(
            user.locked_until,
        )

        self.assertFalse(
            user.is_locked,
        )

        self.assertGreater(
            user.locked_until,
            timezone.now(),
        )

    # --------------------------------------------------
    # Permanent lock escalation
    # --------------------------------------------------

    def test_failed_logins_trigger_permanent_lock(
        self,
    ):

        policy = SecuritySettings.objects.create(
            enable_account_lockout=True,
            lockout_attempts=3,
            permanent_lock_threshold=5,
        )

        user = UserFactory()

        for _ in range(5):

            register_failed_login(
                user=user,
                policy=policy,
            )

        user.refresh_from_db()

        self.assertTrue(
            user.is_locked,
        )

        self.assertEqual(
            user.locked_reason,
            (
                "Exceeded maximum "
                "failed login attempts"
            ),
        )

    # --------------------------------------------------
    # Reset failed login state
    # --------------------------------------------------

    def test_reset_failed_logins_clears_security_state(
        self,
    ):

        user = UserFactory(
            failed_login_attempts=5,
            is_locked=True,
            locked_until=timezone.now(),
        )

        reset_failed_logins(user)

        user.refresh_from_db()

        self.assertEqual(
            user.failed_login_attempts,
            0,
        )

        self.assertIsNone(
            user.locked_until,
        )

        self.assertIsNone(
            user.last_failed_login_at,
        )

    # --------------------------------------------------
    # Validation checks
    # --------------------------------------------------

    def test_validate_user_not_locked_rejects_permanent_lock(
        self,
    ):

        user = UserFactory(
            is_locked=True,
        )

        with self.assertRaises(
            AuthenticationFailed,
        ):

            validate_user_not_locked(
                user,
            )

    def test_validate_user_not_locked_rejects_temp_lock(
        self,
    ):

        user = UserFactory(
            locked_until=(
                timezone.now()
            ),
        )

        user.locked_until = (
            timezone.now()
            + timezone.timedelta(
                minutes=15,
            )
        )

        user.save(
            update_fields=[
                "locked_until",
            ],
        )

        with self.assertRaises(
            AuthenticationFailed,
        ):

            validate_user_not_locked(
                user,
            )
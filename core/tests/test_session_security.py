from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from core.models.security import SecuritySettings
from core.models.sessions import UserSession
from core.services.security.login_failures import (
    register_failed_login,
    reset_failed_logins,
    validate_user_not_locked,
)
from users.factories.user_factories import UserFactory


TEST_UA = "unittest-agent"
TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "session-security-tests",
    }
}


@override_settings(CACHES=TEST_CACHES)
class SessionSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.login_url = reverse("login")
        cls.refresh_url = reverse("session_refresh")
        cls.user = UserFactory(
            is_active=True,
            password="StrongPass123!",
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @staticmethod
    def _session_cookie(response):
        session_id = response.json()["session_id"]
        cookie_name = f"refresh_{session_id}"
        return session_id, cookie_name, response.cookies[cookie_name].value

    def _login(self, client=None):
        client = client or self.client
        return client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": "StrongPass123!",
            },
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )

    def test_login_revokes_oldest_session_when_session_limit_reached(self):
        SecuritySettings.objects.create(max_concurrent_sessions=2)

        self._login()
        self._login()
        self._login()

        sessions = UserSession.objects.filter(user=self.user)
        active_sessions = sessions.filter(
            status=UserSession.Status.ACTIVE,
        )
        revoked_sessions = sessions.filter(
            status=UserSession.Status.REVOKED,
        )

        self.assertEqual(active_sessions.count(), 2)
        self.assertEqual(revoked_sessions.count(), 1)

        oldest = sessions.order_by("created_at").first()
        self.assertEqual(oldest.status, UserSession.Status.REVOKED)

    def test_login_ignores_existing_legacy_refresh_cookie(self):
        self.client.cookies["refresh"] = "attacker-controlled-cookie"

        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        _, _, new_refresh = self._session_cookie(response)
        self.assertNotEqual(new_refresh, "attacker-controlled-cookie")

        # Login removes the former shared cookie during migration.
        self.assertIn("refresh", response.cookies)
        self.assertEqual(response.cookies["refresh"].value, "")

        self.assertEqual(
            UserSession.objects.filter(user=self.user).count(),
            1,
        )

    def test_refresh_tokens_are_unique_and_secure(self):
        response1 = self._login()
        _, _, token1 = self._session_cookie(response1)

        response2 = self._login()
        _, _, token2 = self._session_cookie(response2)

        self.assertNotEqual(token1, token2)
        self.assertGreaterEqual(len(token1), 40)
        self.assertGreaterEqual(len(token2), 40)

    def test_refresh_token_cannot_be_used_for_another_session(self):
        response_a = self._login()
        _, _, token_a = self._session_cookie(response_a)

        user_b = UserFactory(
            is_active=True,
            password="StrongPass123!",
        )
        client_b = APIClient()

        response_b = client_b.post(
            self.login_url,
            {
                "email": user_b.email,
                "password": "StrongPass123!",
            },
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

        session_b_id = response_b.json()["session_id"]
        session_b_cookie = f"refresh_{session_b_id}"

        # Put session A's credential under session B's cookie name.
        client_b.cookies[session_b_cookie] = token_a

        refresh_response = client_b.post(
            self.refresh_url,
            format="json",
            HTTP_X_SESSION_ID=str(session_b_id),
            HTTP_USER_AGENT=TEST_UA,
        )

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertNotIn("access", refresh_response.json())

        session_b = UserSession.objects.get(id=session_b_id)
        self.assertEqual(session_b.user_id, user_b.id)
        self.assertEqual(session_b.status, UserSession.Status.ACTIVE)


@override_settings(CACHES=TEST_CACHES)
class LoginFailureServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_failed_logins_trigger_temp_lock(self):
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

        self.assertIsNotNone(user.locked_until)
        self.assertFalse(user.is_locked)
        self.assertGreater(user.locked_until, timezone.now())

    def test_failed_logins_trigger_permanent_lock(self):
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

        self.assertTrue(user.is_locked)
        self.assertEqual(
            user.locked_reason,
            "Exceeded maximum failed login attempts",
        )

    def test_reset_failed_logins_clears_security_state(self):
        user = UserFactory(
            failed_login_attempts=5,
            is_locked=True,
            locked_until=timezone.now(),
        )

        reset_failed_logins(user)
        user.refresh_from_db()

        self.assertEqual(user.failed_login_attempts, 0)
        self.assertIsNone(user.locked_until)
        self.assertIsNone(user.last_failed_login_at)

    def test_validate_user_not_locked_rejects_permanent_lock(self):
        user = UserFactory(is_locked=True)

        with self.assertRaises(AuthenticationFailed):
            validate_user_not_locked(user)

    def test_validate_user_not_locked_rejects_temp_lock(self):
        user = UserFactory(
            locked_until=timezone.now() + timezone.timedelta(minutes=15),
        )

        with self.assertRaises(AuthenticationFailed):
            validate_user_not_locked(user)
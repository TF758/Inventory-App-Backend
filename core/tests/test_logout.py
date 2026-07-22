import secrets
import uuid
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import UserSession
from users.factories.user_factories import UserFactory


TEST_UA = "unittest-agent"


@mock.patch(
    "core.viewsets.general_viewsets.LogoutAPIView.throttle_classes",
    new=[],
)
class LogoutAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("logout")
        self.user = UserFactory(is_active=True)
        self.user.set_password("StrongPass123!")
        self.user.save()

    @staticmethod
    def _cookie_name(session_id):
        return f"refresh_{session_id}"

    def _post_logout(self, session_id):
        return self.client.post(
            self.url,
            format="json",
            HTTP_X_SESSION_ID=str(session_id),
            HTTP_USER_AGENT=TEST_UA,
        )

    def _make_session_with_cookie(
        self,
        *,
        status_value=UserSession.Status.ACTIVE,
    ):
        raw_refresh = secrets.token_urlsafe(32)
        now = timezone.now()

        session = UserSession.objects.create(
            user=self.user,
            refresh_token_hash=UserSession.hash_token(raw_refresh),
            previous_refresh_token_hash=None,
            status=status_value,
            expires_at=now + timedelta(days=7),
            absolute_expires_at=now + timedelta(days=30),
            user_agent=TEST_UA,
            user_agent_hash=UserSession.hash_user_agent(TEST_UA),
            ip_address="127.0.0.1",
        )

        self.client.cookies[self._cookie_name(session.id)] = raw_refresh
        return session, raw_refresh

    def test_logout_successful_revokes_session_and_deletes_cookie(self):
        session, _ = self._make_session_with_cookie()
        cookie_name = self._cookie_name(session.id)

        response = self._post_logout(session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.json()["detail"])
        self.assertIn(cookie_name, response.cookies)
        self.assertEqual(response.cookies[cookie_name].value, "")

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.REVOKED)

    def test_logout_missing_cookie_returns_200(self):
        session_id = uuid.uuid4()
        cookie_name = self._cookie_name(session_id)

        response = self._post_logout(session_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.json()["detail"])
        self.assertIn(cookie_name, response.cookies)

    def test_logout_invalid_token_returns_200(self):
        session, _ = self._make_session_with_cookie()
        self.client.cookies[self._cookie_name(session.id)] = "invalid-token"

        response = self._post_logout(session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.json()["detail"])

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.ACTIVE)

    def test_logout_already_revoked_session_returns_200(self):
        session, raw_refresh = self._make_session_with_cookie(
            status_value=UserSession.Status.REVOKED,
        )
        self.client.cookies[self._cookie_name(session.id)] = raw_refresh

        response = self._post_logout(session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.json()["detail"])

    def test_logout_hashing_failure_returns_500(self):
        session, _ = self._make_session_with_cookie()

        with mock.patch(
            "core.viewsets.general_viewsets.UserSession.hash_token",
            side_effect=Exception("Hashing failed"),
        ):
            response = self._post_logout(session.id)

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def test_logout_db_save_failure_returns_500(self):
        session, _ = self._make_session_with_cookie()

        with mock.patch.object(
            UserSession,
            "save",
            side_effect=Exception("DB write error"),
        ):
            response = self._post_logout(session.id)

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.ACTIVE)

    def test_logout_only_revokes_target_session(self):
        session1, _ = self._make_session_with_cookie()

        session2_raw = secrets.token_urlsafe(32)
        now = timezone.now()
        session2 = UserSession.objects.create(
            user=self.user,
            refresh_token_hash=UserSession.hash_token(session2_raw),
            previous_refresh_token_hash=None,
            status=UserSession.Status.ACTIVE,
            expires_at=now + timedelta(days=7),
            absolute_expires_at=now + timedelta(days=30),
            user_agent="Device-B",
            user_agent_hash=UserSession.hash_user_agent("Device-B"),
            ip_address="127.0.0.2",
        )

        response = self._post_logout(session1.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session1.refresh_from_db()
        session2.refresh_from_db()

        self.assertEqual(session1.status, UserSession.Status.REVOKED)
        self.assertEqual(session2.status, UserSession.Status.ACTIVE)

    def test_logout_is_idempotent(self):
        session, raw_refresh = self._make_session_with_cookie()
        cookie_name = self._cookie_name(session.id)

        first_response = self._post_logout(session.id)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        self.client.cookies[cookie_name] = raw_refresh
        second_response = self._post_logout(session.id)

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "Successfully logged out",
            second_response.json()["detail"],
        )
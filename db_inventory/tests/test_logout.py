from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest import mock
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import secrets

from db_inventory.models import UserSession
from db_inventory.factories import UserFactory


@mock.patch(
    "db_inventory.viewsets.general_viewsets.LogoutAPIView.throttle_classes",
    new=[]
)
class LogoutAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("logout")
        self.user = UserFactory(is_active=True)
        self.user.set_password("StrongPass123!")
        self.user.save()

    def _make_session_with_cookie(self, *, status_value=UserSession.Status.ACTIVE):
        """
        Creates a UserSession whose refresh_token_hash matches the cookie we attach.
        Returns: (session, raw_refresh)
        """
        raw_refresh = secrets.token_urlsafe(32)
        now = timezone.now()

        session = UserSession.objects.create(
            user=self.user,
            refresh_token_hash=UserSession.hash_token(raw_refresh),
            previous_refresh_token_hash=None,
            status=status_value,
            expires_at=now + timedelta(days=7),
            absolute_expires_at=now + timedelta(days=30),
            user_agent="unittest-agent",
            user_agent_hash=UserSession.hash_user_agent("unittest-agent"),
            ip_address="127.0.0.1",
        )

        self.client.cookies["refresh"] = raw_refresh
        return session, raw_refresh

    # --------------------
    # HAPPY PATH
    # --------------------
    def test_logout_successful_revokes_session_and_deletes_cookie(self):
        session, _ = self._make_session_with_cookie()

        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.json()["detail"])

        self.assertIn("refresh", response.cookies)
        self.assertEqual(response.cookies["refresh"].value, "")

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.REVOKED)

    # --------------------
    # FAILURE CASES
    # --------------------
    def test_logout_missing_cookie_returns_400(self):
        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No refresh token", response.json()["detail"])

    def test_logout_invalid_token_returns_400(self):
        self.client.cookies["refresh"] = "invalid-token"
        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or expired session", response.json()["detail"])

    def test_logout_already_revoked_session_returns_400(self):
        session, raw_refresh = self._make_session_with_cookie(
            status_value=UserSession.Status.REVOKED
        )
        self.client.cookies["refresh"] = raw_refresh

        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or expired session", response.json()["detail"])

    # --------------------
    # EXCEPTION PATHS
    # --------------------
    def test_logout_hashing_failure_returns_500(self):
        _, raw_refresh = self._make_session_with_cookie()

        with mock.patch(
            "db_inventory.models.UserSession.hash_token",
            side_effect=Exception("Hashing failed"),
        ):
            response = self.client.post(self.url, format="json")

        self.assertIn(response.status_code, (500, 503))

    def test_logout_db_save_failure_returns_500(self):
        session, _ = self._make_session_with_cookie()

        with mock.patch.object(
            UserSession,
            "save",
            side_effect=Exception("DB write error"),
        ):
            response = self.client.post(self.url, format="json")

        self.assertIn(response.status_code, (500, 503))

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.ACTIVE)

    # --------------------
    # EDGE CASES
    # --------------------
    def test_logout_only_revokes_target_session(self):
        session1, raw_refresh1 = self._make_session_with_cookie()
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

        # Cookie points to session1
        self.client.cookies["refresh"] = raw_refresh1

        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session1.refresh_from_db()
        session2.refresh_from_db()
        self.assertEqual(session1.status, UserSession.Status.REVOKED)
        self.assertEqual(session2.status, UserSession.Status.ACTIVE)

    def test_logout_is_idempotent(self):
        session, raw_refresh = self._make_session_with_cookie()

        # first logout succeeds
        resp1 = self.client.post(self.url, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        # reuse same cookie -> should now fail safely
        self.client.cookies["refresh"] = raw_refresh
        resp2 = self.client.post(self.url, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or expired session", resp2.json()["detail"])

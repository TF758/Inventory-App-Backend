from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest import mock
from django.urls import reverse
from db_inventory.models import UserSession, User
from db_inventory.factories import UserFactory
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError


@mock.patch(
    "db_inventory.viewsets.general_viewsets.LogoutAPIView.throttle_classes",
    new=[]
)
class LogoutAPIViewTests(TestCase):
    """Tests for LogoutAPIView (revokes session and deletes refresh cookie)"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("logout")  # Make sure this matches your URL name
        self.user = UserFactory(is_active=True)
        self.user.set_password("StrongPass123!")
        self.user.save()

    def _create_session_and_attach_cookie(self):
        """Helper to create a user session and attach its refresh token to the client."""
        raw_refresh = "raw-refresh-token"
        hashed_refresh = UserSession.hash_token(raw_refresh)
        session = UserSession.objects.create(
            user=self.user,
            refresh_token_hash=hashed_refresh,
            expires_at=timezone.now() + timedelta(days=7),
            ip_address="127.0.0.1",
            user_agent="unittest-agent",
        )
        self.client.cookies["refresh"] = raw_refresh
        return session, raw_refresh

    # --- HAPPY PATH ---
    def test_logout_successful_revokes_session_and_deletes_cookie(self):
        session, raw_refresh = self._create_session_and_attach_cookie()

        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.json()["detail"])
        # Check cookie is cleared
        self.assertEqual(response.cookies["refresh"].value, "")

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.REVOKED)


    # --- FAILURE PATHS ---
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
        session, raw_refresh = self._create_session_and_attach_cookie()
        session.status = UserSession.Status.REVOKED
        session.save(update_fields=["status"])

        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or expired session", response.json()["detail"])

    # --- EXCEPTION PATHS ---
    def test_logout_hashing_failure_returns_500(self):
        self._create_session_and_attach_cookie()
        with mock.patch("db_inventory.models.UserSession.hash_token") as mock_hash:
            mock_hash.side_effect = Exception("Hashing failed")
            response = self.client.post(self.url, format="json")

        self.assertIn(response.status_code, [500, 503])

    def test_logout_db_save_failure_returns_500(self):
        session, raw_refresh = self._create_session_and_attach_cookie()
        with mock.patch.object(UserSession, "save", side_effect=Exception("DB write error")):
            response = self.client.post(self.url, format="json")

        self.assertIn(response.status_code, [500, 503])
        # Ensure session status is unchanged
        session.refresh_from_db()
        self.assertNotEqual(session.status, UserSession.Status.REVOKED)

    # --- EDGE CASES ---
    def test_logout_multiple_sessions_only_target_revoked(self):
        session1, raw_refresh1 = self._create_session_and_attach_cookie()
        session2 = UserSession.objects.create(
            user=self.user,
            refresh_token_hash=UserSession.hash_token("other-token"),
            expires_at=timezone.now() + timedelta(days=7),
            ip_address="127.0.0.2",
            user_agent="Device-B",
        )
        # Use session1 cookie
        response = self.client.post(self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        session1.refresh_from_db()
        session2.refresh_from_db()
        self.assertEqual(session1.status, UserSession.Status.REVOKED)
        self.assertNotEqual(session2.status, UserSession.Status.REVOKED)

    def test_logout_idempotent_behavior(self):
        session, raw_refresh = self._create_session_and_attach_cookie()

        # First logout
        resp1 = self.client.post(self.url, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        # Second logout (reuse cookie)
        self.client.cookies["refresh"] = raw_refresh
        resp2 = self.client.post(self.url, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or expired session", resp2.json()["detail"])

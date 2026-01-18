from datetime import timedelta
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.db import IntegrityError
from unittest import mock

from rest_framework_simplejwt.tokens import AccessToken

from db_inventory.models import UserSession, User
from db_inventory.factories import UserFactory


TEST_UA = "unittest-agent"


@mock.patch(
    "db_inventory.viewsets.general_viewsets.SessionTokenLoginView.throttle_classes",
    new=[]
)
class SessionTokenLoginViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login")

    def _create_active_user(self):
        user = UserFactory(is_active=True)
        user.set_password("StrongPass123!")
        user.save()
        return user

    def test_successful_login_creates_session_and_cookie(self):
        user = self._create_active_user()

        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            HTTP_USER_AGENT=TEST_UA,
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.cookies)
        self.assertTrue(UserSession.objects.filter(user=user).exists())

    def test_concurrent_logins_create_separate_sessions(self):
        user = self._create_active_user()

        client_a = APIClient()
        client_b = APIClient()

        resp_a = client_a.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            HTTP_USER_AGENT="Device-A",
            REMOTE_ADDR="10.0.0.1",
        )
        resp_b = client_b.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            HTTP_USER_AGENT="Device-B",
            REMOTE_ADDR="10.0.0.2",
        )

        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_b.status_code, 200)

        sessions = list(UserSession.objects.filter(user=user))
        self.assertEqual(len(sessions), 2)

        # 🔐 UA hashes must differ (plaintext UA no longer stored)
        self.assertNotEqual(
            sessions[0].user_agent_hash,
            sessions[1].user_agent_hash,
        )


@mock.patch(
    "db_inventory.viewsets.general_viewsets.SessionTokenLoginView.throttle_classes",
    new=[]
)
@mock.patch(
    "db_inventory.viewsets.general_viewsets.RefreshAPIView.throttle_classes",
    new=[]
)
class RefreshTokenViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("login")
        self.refresh_url = reverse("session_refresh")

        self.user = UserFactory(is_active=True)
        self.user.set_password("StrongPass123!")
        self.user.save()

    def _login(self):
        response = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": "StrongPass123!"},
            format="json",
            HTTP_USER_AGENT=TEST_UA,
            REMOTE_ADDR="127.0.0.1",
        )
        self.assertEqual(response.status_code, 200)
        self.client.cookies["refresh"] = response.cookies["refresh"].value
        return response

    # ------------------- HAPPY PATH -------------------

    def test_refresh_successful_returns_new_access_and_cookie(self):
        self._login()

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.cookies)

    def test_refresh_extends_idle_expiry(self):
        self._login()

        session = UserSession.objects.get(user=self.user)
        old_expiry = session.expires_at

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response.status_code, 200)

        session.refresh_from_db()
        expected = timezone.now() + settings.SESSION_IDLE_TIMEOUT
        self.assertAlmostEqual(
            session.expires_at.timestamp(),
            expected.timestamp(),
            delta=5,  # seconds
        )

    def test_refresh_rotates_token_and_invalidates_old_one(self):
        login_response = self._login()
        old_cookie = login_response.cookies["refresh"].value

        session = UserSession.objects.get(user=self.user)
        
        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response.status_code, 200)

        new_cookie = response.cookies["refresh"].value

        # Old cookie must fail
        self.client.cookies["refresh"] = old_cookie
        response2 = self.client.post(self.refresh_url, format="json", HTTP_USER_AGENT=TEST_UA)
        self.assertEqual(response2.status_code, 401)

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.REVOKED)

        # New cookie should ALSO fail after revocation
        self.client.cookies["refresh"] = new_cookie
        response3 = self.client.post(self.refresh_url, format="json", HTTP_USER_AGENT=TEST_UA)
        self.assertEqual(response3.status_code, 401)


    # ------------------- FAILURE MODES -------------------

    def test_missing_refresh_cookie_returns_401(self):
        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_refresh_cookie_returns_401(self):
        self._login()
        self.client.cookies["refresh"] = "invalid"

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response.status_code, 401)

    def test_user_agent_mismatch_revokes_session(self):
        self._login()

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT="evil-agent",
        )
        self.assertEqual(response.status_code, 401)

        session = UserSession.objects.get(user=self.user)
        self.assertEqual(session.status, UserSession.Status.REVOKED)

    # ------------------- TOKEN CLAIMS -------------------

    def test_access_token_includes_expected_claims(self):
        self._login()

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response.status_code, 200)

        token = AccessToken(response.json()["access"])
        session = UserSession.objects.get(user=self.user)

        self.assertEqual(str(token["session_id"]), str(session.id))
        self.assertEqual(str(token["public_id"]), str(self.user.public_id))
        self.assertIn("abs_exp", token)

    # ------------------- COOKIE SECURITY -------------------

    def test_refresh_cookie_has_secure_flags(self):
        self._login()

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )
        self.assertEqual(response.status_code, 200)

        cookie = response.cookies["refresh"]
        self.assertEqual(bool(cookie["secure"]), settings.COOKIE_SECURE)
        self.assertEqual(cookie["samesite"], settings.COOKIE_SAMESITE)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/")

    def test_refresh_fails_after_absolute_expiry(self):
        self._login()

        session = UserSession.objects.get(user=self.user)
        session.absolute_expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["absolute_expires_at"])

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )

        self.assertEqual(response.status_code, 401)

        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.EXPIRED)

    def test_refresh_fails_when_session_revoked(self):
        self._login()

        session = UserSession.objects.get(user=self.user)
        session.status = UserSession.Status.REVOKED
        session.save(update_fields=["status"])

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )

        self.assertEqual(response.status_code, 401)

    def test_access_token_rejected_when_session_expired(self):
        login_response = self._login()
        token = login_response.json()["access"]

        session = UserSession.objects.get(user=self.user)
        session.expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=["expires_at"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        protected_url = reverse("departments")
        response = self.client.get(protected_url)

        self.assertEqual(response.status_code, 401)

    def test_refresh_fails_for_locked_user(self):
        self._login()
        self.user.is_locked = True
        self.user.save(update_fields=["is_locked"])

        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_USER_AGENT=TEST_UA,
        )

        self.assertEqual(response.status_code, 403)


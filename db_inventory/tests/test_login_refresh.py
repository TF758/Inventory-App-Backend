from datetime import timedelta
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from db_inventory.models import UserSession, User
from db_inventory.factories import UserFactory
from unittest import mock
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from django.db import IntegrityError
from django.test import override_settings


@mock.patch(
    "db_inventory.viewsets.general_viewsets.SessionTokenLoginView.throttle_classes",
    new=[]
)
class SessionTokenLoginViewTests(TestCase):
    """
    Tests for the SessionTokenLoginView (JWT + DB-backed refresh sessions)
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login")

    def _create_active_user(self):
        """Helper to create an active test user with known credentials."""
        user = UserFactory(is_active=True)
        user.set_password("StrongPass123!")
        user.public_id = "user-public-id"
        user.active_role = None
        user.save()
        return user

    def test_successful_login_creates_session_and_cookie(self):
        user = self._create_active_user()

        self.assertTrue(
            User.objects.filter(email=user.email).exists(),
            msg="The test user should exist in the database before login."
        )
        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            REMOTE_ADDR="127.0.0.1",
            HTTP_USER_AGENT="unittest-agent",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cookie = response.cookies.get("refresh")
        self.assertIsNotNone(cookie)
        self.assertTrue(UserSession.objects.filter(user=user).exists())

    def test_invalid_credentials_returns_401(self):
        response = self.client.post(
            self.url,
            {"email": "nosuchuser@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(UserSession.objects.count(), 0)

    def test_login_user_without_active_role(self):
        user = self._create_active_user()
        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["role_id"])

    def test_inactive_user_cannot_login(self):
        """Inactive users should not be able to log in."""
        user = self._create_active_user()
        user.is_active = False
        user.save()

        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(UserSession.objects.count(), 0)

    def test_missing_credentials_returns_400(self):
        """Missing username/password should raise validation error."""
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_request_data_returns_400(self):
        """Improper payload keys should cause serializer validation failure."""
        response = self.client.post(
            self.url,
            {"email": "wrongfield@example.com", "passcode": "bad"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concurrent_logins_create_separate_sessions(self):
        """
         Test multiple concurrent logins:
        - User logs in from different devices (different user agents)
        - Each login creates a unique UserSession
        - Each refresh cookie is unique
        """
        user = self._create_active_user()

        client_a = APIClient()
        client_b = APIClient()

        # Simulate two devices
        resp_a = client_a.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            REMOTE_ADDR="10.0.0.1",
            HTTP_USER_AGENT="Device-A",
        )
        resp_b = client_b.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            REMOTE_ADDR="10.0.0.2",
            HTTP_USER_AGENT="Device-B",
        )

        # Both should succeed
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_b.status_code, 200)

        # Both should have cookies
        cookie_a = resp_a.cookies.get("refresh")
        cookie_b = resp_b.cookies.get("refresh")
        self.assertIsNotNone(cookie_a)
        self.assertIsNotNone(cookie_b)
        self.assertNotEqual(cookie_a.value, cookie_b.value)

        # Verify DB sessions
        sessions = UserSession.objects.filter(user=user)
        self.assertEqual(sessions.count(), 2)

        session_ips = {s.ip_address for s in sessions}
        session_agents = {s.user_agent for s in sessions}

        self.assertIn("10.0.0.1", session_ips)
        self.assertIn("10.0.0.2", session_ips)
        self.assertIn("Device-A", session_agents)
        self.assertIn("Device-B", session_agents)

        # Each session should expire in about 1 day
        for session in sessions:
            delta = session.expires_at - timezone.localtime(timezone.now())
            self.assertTrue(timedelta(hours=23) <= delta <= timedelta(hours=25))

    
        # handling cookies correctly 
    def test_no_cookie_set_on_failed_login(self):
        """No refresh cookie should be returned for failed authentication."""
        response = self.client.post(
            self.url,
            {"email": "wrong@example.com", "password": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("refresh", response.cookies)

    def test_cookie_overwritten_on_subsequent_login(self):
        """A new refresh cookie should overwrite any existing cookie value."""
        user = self._create_active_user()

        # First login
        first_resp = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        first_cookie = first_resp.cookies.get("refresh").value

        # Second login (simulate later session)
        second_resp = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        second_cookie = second_resp.cookies.get("refresh").value

        self.assertNotEqual(first_cookie, second_cookie)
        self.assertEqual(UserSession.objects.filter(user=user).count(), 2)


    @mock.patch("db_inventory.models.UserSession.hash_token")
    def test_refresh_token_hash_failure_returns_500(self, mock_hash):
        """Simulate failure when hashing the refresh token."""
        user = self._create_active_user()
        mock_hash.side_effect = Exception("Hashing failed")

        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertIn(response.status_code, [500, 503])
        self.assertEqual(UserSession.objects.count(), 0)


    @mock.patch("db_inventory.models.UserSession.objects.create")
    def test_user_session_integrity_error_returns_500(self, mock_create):
        """Simulate IntegrityError when creating UserSession."""
        user = self._create_active_user()
        mock_create.side_effect = IntegrityError("Unique constraint failed")

        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertIn(response.status_code, [500, 503])
        self.assertEqual(UserSession.objects.count(), 0)


    @mock.patch("db_inventory.models.UserSession.objects.create")
    def test_user_session_unexpected_exception_returns_500(self, mock_create):
        """Simulate unexpected DB error during UserSession creation."""
        user = self._create_active_user()
        mock_create.side_effect = Exception("Unexpected DB failure")

        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertIn(response.status_code, [500, 503])
        self.assertEqual(UserSession.objects.count(), 0)

    @mock.patch("rest_framework_simplejwt.tokens.AccessToken.for_user")
    def test_access_token_generation_failure_cleans_up_session(self, mock_token):
        """If JWT generation fails, session should be deleted."""
        user = self._create_active_user()
        mock_token.side_effect = Exception("JWT signing error")

        response = self.client.post(
            self.url,
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertIn(response.status_code, [500, 503])
        self.assertEqual(UserSession.objects.count(), 0)

@mock.patch(
    "db_inventory.viewsets.general_viewsets.SessionTokenLoginView.throttle_classes",
    new=[]
)
@mock.patch(
    "db_inventory.viewsets.general_viewsets.RefreshAPIView.throttle_classes",
    new=[]
)
class RefreshTokenViewTests(TestCase):
    """Tests for RefreshAPIView behavior and token rotation."""

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("login")
        self.refresh_url = reverse("session_refresh")
        self.raw_password = "StrongPass123!"
        self.user = UserFactory(is_active=True)
        self.user.set_password(self.raw_password)
        self.user.save()

  
    def _login_and_attach_cookie(self):
        """Helper: logs in user and attaches refresh cookie to client."""
        response = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": self.raw_password},
            format="json",
            REMOTE_ADDR="127.0.0.1",
            HTTP_USER_AGENT="unittest-agent",
        )

        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            f"Login failed during setup: {response.status_code}"
        )
        self.assertIn("refresh", response.cookies)

        refresh_cookie = response.cookies["refresh"]
        self.client.cookies["refresh"] = refresh_cookie.value
        return response

    def test_login_precondition(self):
        """Ensure a valid login creates a refresh cookie and session."""
        response = self._login_and_attach_cookie()

        self.assertTrue(
            UserSession.objects.filter(user=self.user).exists(),
            "Login should create an active UserSession"
        )



    # # --- HAPPY PATH ---
    def test_refresh_successful_returns_new_access_and_cookie(self):
        """Valid refresh token returns new access token and sets new cookie."""
        login_response = self._login_and_attach_cookie()
        raw_refresh = login_response.cookies["refresh"].value

        # Manually send the cookie in the HTTP request
        response = self.client.post(
            self.refresh_url,
            format="json",
            HTTP_COOKIE=f"refresh={raw_refresh}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", response.cookies)

    def test_refresh_extends_expiry_by_seven_days(self):
        """Ensure session expiry is extended after refresh."""
        # Log in and attach cookie
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        # Get the session created by login
        session = UserSession.objects.filter(user=self.user).first()
        old_expiry = session.expires_at

        # Perform refresh
        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh session from DB
        session.refresh_from_db()
        self.assertGreater(session.expires_at, old_expiry)
        delta = session.expires_at - old_expiry
        self.assertTrue(6 <= delta.days <= 8)  # allow small rounding diff

    def test_refresh_rotates_token_and_invalidates_old_one(self):
        """After rotation, old refresh cookie no longer works."""

        # Perform login and attach refresh cookie
        login_response = self._login_and_attach_cookie()
        old_cookie_value = login_response.cookies["refresh"].value

        # First refresh request succeeds
        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Store new refresh cookie
        new_cookie_value = response.cookies["refresh"].value

        # Old cookie should no longer work
        self.client.cookies["refresh"] = old_cookie_value
        response2 = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid or expired session", response2.json()["detail"])

        # New cookie should work
        self.client.cookies["refresh"] = new_cookie_value
        response3 = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response3.status_code, status.HTTP_200_OK)


    # --- MISSING COOKIE TEST ---
    def test_missing_refresh_cookie_returns_400(self):
        """Request without refresh cookie should return 400."""
        self._login_and_attach_cookie()  
        self.client.cookies.clear()       # remove cookie
        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("No refresh token", response.json()["detail"])


    # --- INVALID COOKIE TEST ---
    def test_invalid_refresh_cookie_returns_401(self):
        """Nonexistent token hash should return 401."""
        self._login_and_attach_cookie()
        self.client.cookies["refresh"] = "bad_token"  # invalid token
        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid or expired session", response.json()["detail"])


    def test_expired_session_returns_401(self):
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        # Expire the session
        session = UserSession.objects.filter(user=self.user).first()
        session.expires_at = timezone.now() - timedelta(hours=1)
        session.save(update_fields=["expires_at"])

        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("expired", response.json()["detail"])

        # NEW: ensure the session status is updated
        session.refresh_from_db()
        self.assertEqual(session.status, UserSession.Status.EXPIRED)


    def test_access_token_fails_when_session_expired(self):
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        # Expire the session
        session = UserSession.objects.filter(user=self.user).first()
        session.expires_at = timezone.now() - timedelta(minutes=1)
        session.save(update_fields=["expires_at"])

        # Use the JWT from login
        token_str = login_response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_str}")

        # Make a request to a protected endpoint
        protected_url = reverse("departments")  # replace with an actual view
        response = self.client.get(protected_url)
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["detail"])


    def test_revoked_session_returns_401(self):
        """Revoked sessions should not be refreshed."""
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        # Revoke the session
        session = UserSession.objects.filter(user=self.user).first()
        session.status = UserSession.Status.REVOKED
        session.save(update_fields=["status"])

        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid or expired session", response.json()["detail"])


    # --- ACCESS TOKEN PAYLOAD INTEGRITY ---
    def test_access_token_includes_expected_claims(self):
        """New JWT should include user identifiers and session ID."""
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token_str = response.json()["access"]
        token = AccessToken(token_str)

        session = UserSession.objects.filter(user=self.user).first()

        self.assertEqual(str(token["session_id"]), str(session.id))
        self.assertEqual(str(token["public_id"]), str(self.user.public_id))
        self.assertIn("role_id", token)

    # --- COOKIE SECURITY ---
    def test_refresh_cookie_has_secure_flags(self):
        """Refresh cookie should be secure, HttpOnly, and same-site None."""

        # Perform login and attach cookie
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        # Perform refresh to get new cookie
        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        cookie = response.cookies.get("refresh")
        self.assertIsNotNone(cookie, "Refresh cookie was not set in response")
        self.assertTrue(cookie["httponly"], "Refresh cookie should be HttpOnly")
        self.assertTrue(cookie["secure"], "Refresh cookie should be Secure")
        self.assertEqual(cookie["samesite"], "None", "Refresh cookie should have SameSite=None")
        self.assertEqual(cookie["path"], "/", "Refresh cookie path should be '/'")


  # --- FAILURE & EDGE CASES ---
    def test_hash_function_failure_returns_500(self):
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        with mock.patch("db_inventory.models.UserSession.hash_token") as mock_hash:
            mock_hash.side_effect = Exception("Hash failed")
            response = self.client.post(self.refresh_url, format="json")

        self.assertIn(response.status_code, [500, 503])

    def test_access_token_generation_failure_returns_500(self):
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        with mock.patch("rest_framework_simplejwt.tokens.AccessToken.for_user") as mock_for_user:
            mock_for_user.side_effect = Exception("JWT signing error")
            response = self.client.post(self.refresh_url, format="json")

        self.assertIn(response.status_code, [500, 503])

    def test_session_save_failure_returns_500(self):
        login_response = self._login_and_attach_cookie()
        self.client.cookies["refresh"] = login_response.cookies["refresh"].value

        with mock.patch("db_inventory.models.UserSession.save") as mock_save:
            mock_save.side_effect = Exception("DB write error")
            response = self.client.post(self.refresh_url, format="json")


    def test_concurrent_refresh_only_first_succeeds(self):
        """If two refreshes use same cookie, only the first one works."""
        login_response = self._login_and_attach_cookie()
        old_cookie_value = login_response.cookies["refresh"].value

        # First refresh should succeed
        response1 = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Reuse old cookie (stale)
        self.client.cookies["refresh"] = old_cookie_value
        response2 = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid or expired session", response2.json()["detail"])

    def test_refresh_rotates_token_and_invalidates_old_one(self):
        """After rotation, old refresh cookie no longer works, and session is updated in DB."""

        # Perform login and attach refresh cookie
        login_response = self._login_and_attach_cookie()
        old_cookie_value = login_response.cookies["refresh"].value

        # Get the session before refresh
        session = UserSession.objects.filter(user=self.user).first()
        old_hash = session.refresh_token_hash
        old_expiry = session.expires_at

        # First refresh request succeeds
        response = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_cookie_value = response.cookies["refresh"].value

        # Refresh session from DB
        session.refresh_from_db()
        
        # Check DB changes
        self.assertNotEqual(session.refresh_token_hash, old_hash, "Refresh token hash should be rotated")
        self.assertGreater(session.expires_at, old_expiry, "Session expiry should be extended")
        self.assertEqual(session.status, UserSession.Status.ACTIVE, "Session should remain active after rotation")

        # Old cookie should no longer work
        self.client.cookies["refresh"] = old_cookie_value
        response2 = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid or expired session", response2.json()["detail"])

        # New cookie should work
        self.client.cookies["refresh"] = new_cookie_value
        response3 = self.client.post(self.refresh_url, format="json")
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
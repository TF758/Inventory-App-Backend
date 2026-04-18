from db_inventory.models.security import SecuritySettings, UserSession
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken

from users.factories.user_factories import UserFactory


class SessionSecurityTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("login")
        self.refresh_url = reverse("session_refresh")

        self.user = UserFactory(is_active=True)
        self.user.set_password("StrongPass123!")
        self.user.save()

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
    

    def test_login_revokes_oldest_session_when_session_limit_reached(self):

        SecuritySettings.objects.create(max_concurrent_sessions=2)

        self._login()
        self._login()
        self._login()

        sessions = UserSession.objects.filter(user=self.user)

        active_sessions = sessions.filter(status=UserSession.Status.ACTIVE)
        revoked_sessions = sessions.filter(status=UserSession.Status.REVOKED)

        self.assertEqual(active_sessions.count(), 2)
        self.assertEqual(revoked_sessions.count(), 1)

        oldest = sessions.order_by("created_at").first()
        self.assertEqual(oldest.status, UserSession.Status.REVOKED)


    def test_login_ignores_existing_refresh_cookie(self):

        self.client.cookies["refresh"] = "attacker-controlled-cookie"

        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_cookie = response.cookies["refresh"].value

        self.assertNotEqual(new_cookie, "attacker-controlled-cookie")

        sessions = UserSession.objects.filter(user=self.user)
        self.assertEqual(sessions.count(), 1)


    def test_refresh_tokens_are_unique_and_secure(self):

        resp1 = self._login()
        token1 = resp1.cookies["refresh"].value

        resp2 = self._login()
        token2 = resp2.cookies["refresh"].value

        self.assertNotEqual(token1, token2)

        # ensure token length is sufficiently large
        self.assertGreaterEqual(len(token1), 40)
        self.assertGreaterEqual(len(token2), 40)


    def test_refresh_token_cannot_be_used_by_another_user(self):

        # login user A
        resp_a = self._login()
        refresh_token = resp_a.cookies["refresh"].value

        # create user B
        user_b = UserFactory(is_active=True)
        user_b.set_password("StrongPass123!")
        user_b.save()

        client_b = APIClient()

        # login user B
        login_b = client_b.post(
            self.login_url,
            {
                "email": user_b.email,
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(login_b.status_code, status.HTTP_200_OK)

        # attacker tries to use A's refresh token
        client_b.cookies["refresh"] = refresh_token

        response = client_b.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        access_token = response.json()["access"]
        payload = AccessToken(access_token)

        session_id = payload["session_id"]

        session = UserSession.objects.get(id=session_id)

        # verify session belongs to original user (user A)
        self.assertEqual(session.user_id, self.user.id)

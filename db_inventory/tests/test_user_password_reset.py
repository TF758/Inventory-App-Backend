from django.conf import settings
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APITestCase
from unittest.mock import patch
from db_inventory.models import User
from db_inventory.factories import UserFactory
from db_inventory.utils.tokens import PasswordResetToken



# ----------------------------------------------------------------------
# Fake failing backend
# ----------------------------------------------------------------------
class FailingEmailBackend:
    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, email_messages):
        raise Exception("Simulated email backend failure")


@patch(
    "db_inventory.viewsets.general_viewsets.PasswordResetRequestView.throttle_classes",
    new=[]
)
class PasswordResetRequestTests(TestCase):

    def setUp(self):
        self.active_user = UserFactory(email="active@example.com", is_active=True)
        self.inactive_user = UserFactory(email="inactive@example.com", is_active=False)

    def test_password_reset_request_success(self):
        url = reverse("password-reset-request")

        response = self.client.post(url, {"email": self.active_user.email}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"],"If an account exists, a password reset email has been sent.")

    def test_password_reset_request_user_not_found(self):
        url = reverse("password-reset-request")

        response = self.client.post(url, {"email": "missing@example.com"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"],"If an account exists, a password reset email has been sent.")

    def test_password_reset_request_inactive_user(self):
        url = reverse("password-reset-request")

        response = self.client.post(url, {"email": self.inactive_user.email}, format="json")

        # View intentionally returns 200 even for inactive users
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"],"If an account exists, a password reset email has been sent.")

    def test_only_last_token_active(self):
        user = UserFactory(email="multi@example.com", is_active=True)

        service = PasswordResetToken()  # use single consistent instance

        # STEP 1 — generate first token
        event1 = service.generate_token(user.public_id)
        result1_initial = service.verify_token(event1.token)
        self.assertIsNotNone(result1_initial)       # valid

        # STEP 2 — generate second token
        event2 = service.generate_token(user.public_id)
        result2 = service.verify_token(event2.token)
        self.assertIsNotNone(result2)               # valid

        # Old event should now be inactive + invalid
        event1.refresh_from_db()
        self.assertFalse(event1.is_active)

        # Verify again
        result1_final = service.verify_token(event1.token)
        self.assertIsNone(result1_final)

    def test_email_backend_failure(self):
        backend_path = f"{__name__}.FailingEmailBackend"
        url = reverse("password-reset-request")

        with self.settings(EMAIL_BACKEND=backend_path):
            response = self.client.post(url, {"email": self.active_user.email})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Could not send password reset email, please try again later.",
        )

    def test_case_insensitive_email_lookup(self):
        user = UserFactory(email="UserCase@example.com", is_active=True)
        url = reverse("password-reset-request")

        response = self.client.post(url, {"email": "usercase@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"],"If an account exists, a password reset email has been sent.")


# ----------------------------------------------------------------------
# PASSWORD RESET CONFIRM TESTS
# ----------------------------------------------------------------------
class PasswordResetConfirmTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="OldPass123!",
            is_active=True,
        )
        self.url = reverse("password-reset-confirm")

    @patch("db_inventory.utils.tokens.PasswordResetToken.verify_token", return_value=None)
    def test_confirm_expired_token(self, mock_verify):
        """
        Expired or invalid tokens both result in: TOKEN_INVALID
        """
        data = {
            "token": "expired-token",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "TOKEN_INVALID")

    @patch("db_inventory.utils.tokens.PasswordResetToken.verify_token", return_value=None)
    def test_confirm_invalid_token(self, mock_verify):
        data = {
            "token": "invalid-token",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "TOKEN_INVALID")


class PasswordResetTokenExpirationTests(TestCase):

    def test_token_expired(self):
        user = UserFactory(is_active=True)

        service = PasswordResetToken()

        # Generate a token normally
        event = service.generate_token(user.public_id)

        # Force expiration
        event.expires_at = timezone.now() - timezone.timedelta(hours=1)
        event.save()

        # Should now be invalid
        result = service.verify_token(event.token)
        self.assertIsNone(result)

class PasswordResetTokenTamperingTests(TestCase):

    def test_token_signature_tampering(self):
        user = UserFactory(is_active=True)
        service = PasswordResetToken()

        # Generate a valid token
        event = service.generate_token(user.public_id)
        valid_token = event.token

        # Tamper token by altering one character (invalidating signature)
        tampered_token = valid_token[:-1] + (
            "X" if valid_token[-1] != "X" else "Y"
        )

        # Tampering must break verification
        result = service.verify_token(tampered_token)
        self.assertIsNone(result)
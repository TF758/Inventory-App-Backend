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
from db_inventory.models.users import PasswordResetEvent





@patch(
    "db_inventory.viewsets.general_viewsets.PasswordResetRequestView.throttle_classes",
    new=[]
)
class PasswordResetRequestTests(TestCase):

    def setUp(self):
        self.active_user = UserFactory(email="active@example.com", is_active=True)
        self.inactive_user = UserFactory(email="inactive@example.com", is_active=False)
        self.url = reverse("password-reset-request")

    @patch("db_inventory.tasks.send_password_reset_email.delay")
    def test_request_always_returns_200_for_existing_user(self, mock_delay):
        response = self.client.post(self.url, {"email": self.active_user.email})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["detail"],
            "If an account exists, a password reset email has been sent.",
        )
        mock_delay.assert_called_once_with(self.active_user.email)

    @patch("db_inventory.tasks.send_password_reset_email.delay")
    def test_request_always_returns_200_for_missing_user(self, mock_delay):
        response = self.client.post(self.url, {"email": "missing@example.com"})
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once_with("missing@example.com")

    @patch("db_inventory.tasks.send_password_reset_email.delay")
    def test_request_inactive_user_still_returns_200(self, mock_delay):
        response = self.client.post(self.url, {"email": self.inactive_user.email})
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once_with(self.inactive_user.email)

    @patch("db_inventory.tasks.send_password_reset_email.delay")
    def test_case_insensitive_email_lookup(self, mock_delay):
        response = self.client.post(self.url, {"email": "ACTIVE@EXAMPLE.COM"})
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once_with("ACTIVE@EXAMPLE.COM")


    def test_password_reset_cooldown_enforced(self):
        user = UserFactory(is_active=True)
        service = PasswordResetToken()

        event1 = service.generate_token(user.public_id)
        self.assertIsNotNone(event1)

        # Immediate second attempt should not create a new token
        event2 = service.generate_token(user.public_id)
        self.assertIsNone(event2)

        active_tokens = PasswordResetEvent.objects.filter(
            user=user,
            is_active=True,
            used_at__isnull=True,
        )
        self.assertEqual(active_tokens.count(), 1)
        
#---------------------------------
# PASSWORD RESET CONFIRM TESTS
# ----------------------------------------------------------------------
@patch(
    "db_inventory.viewsets.general_viewsets.PasswordResetConfirmView.throttle_classes",
    new=[]
)
class PasswordResetConfirmTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user( email="test@example.com", password="OldPass123!", is_active=True, )
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


@patch(
    "db_inventory.viewsets.general_viewsets.PasswordResetConfirmView.throttle_classes",
    new=[]
)
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
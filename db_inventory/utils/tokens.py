from django.core.signing import TimestampSigner
from django.utils import timezone
from django.db import transaction
import secrets
from datetime import timedelta
from django.db import transaction
from db_inventory.models import PasswordResetEvent, User

class PasswordResetToken:
    EXPIRY_MINUTES = 10

    def __init__(self):
        self.signer = TimestampSigner(salt="password-reset")

    def generate_token(self, user_public_id: str, admin_public_id: str | None = None) -> PasswordResetEvent:
        """
        Creates a new password-reset token for a user.
        Invalidates previous active tokens.
        Returns the created PasswordResetEvent instance.
        """

        # Fetch the acting user
        try:
            user = User.objects.get(public_id=user_public_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        admin_user = None
        if admin_public_id:
            try:
                admin_user = User.objects.get(public_id=admin_public_id)
            except User.DoesNotExist:
                raise ValueError("Admin user not found")

        with transaction.atomic():
            # 1. Invalidate older active tokens
            (
                PasswordResetEvent.objects
                .filter(user=user, is_active=True, used_at__isnull=True)
                .update(is_active=False)
            )

            # 2. Generate secure random token
            raw_token = secrets.token_urlsafe(32)

            # We sign the token with a timestamp to prevent tampering
            signed_token = self.signer.sign(f"{user.public_id}:{raw_token}")

            # 3. Create new reset event
            event = PasswordResetEvent.objects.create(
                user=user,
                admin=admin_user,
                token=signed_token,
                expires_at=timezone.now() + timedelta(minutes=self.EXPIRY_MINUTES),
                is_active=True,
            )

        return event

    def verify_token(self, signed_token: str) -> PasswordResetEvent | None:
        """
        Verifies the token signature & checks DB validity.
        Returns the valid PasswordResetEvent or None.
        """

        try:
            # Ensure signature is correct
            value = self.signer.unsign(signed_token, max_age=self.EXPIRY_MINUTES * 60)
            user_public_id, raw_token = value.split(":", 1)
        except Exception:
            return None

        try:
            event = PasswordResetEvent.objects.get(token=signed_token)
        except PasswordResetEvent.DoesNotExist:
            return None

        if not event.is_active or not event.is_valid():
            return None

        return event
    
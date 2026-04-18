from django.core.signing import TimestampSigner
from django.utils import timezone
from django.db import transaction
import secrets
from datetime import timedelta
from django.db import transaction
from django.core.signing import SignatureExpired, BadSignature
from db_inventory.models.users import PasswordResetEvent
from users.models.users import User

class PasswordResetToken:
    EXPIRY_MINUTES = 10
    COOLDOWN_MINUTES = 2

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
        
        recent_token_exists = PasswordResetEvent.objects.filter(
            user=user,
            is_active=True,
            used_at__isnull=True,
            created_at__gte=timezone.now() - timedelta(minutes=self.COOLDOWN_MINUTES),
        ).exists()

        if recent_token_exists:
            return None

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

    def verify_token(self, signed_token: str):
        """
        Returns:
            (event, "valid" | "expired" | "invalid")
        """

        try:
            self.signer.unsign(
                signed_token,
                max_age=self.EXPIRY_MINUTES * 60
            )
        except SignatureExpired:
            return None, "expired"
        except BadSignature:
            return None, "invalid"
        except Exception:
            return None, "invalid"

        try:
            event = PasswordResetEvent.objects.get(token=signed_token)
        except PasswordResetEvent.DoesNotExist:
            return None, "invalid"

        if not event.is_active:
            return None, "invalid"

        if not event.is_valid():
            return None, "expired"

        return event, "valid"

    
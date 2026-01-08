from rest_framework import serializers
from db_inventory.models.users import User
from db_inventory.utils.tokens import PasswordResetToken
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class SessionTokenLoginViewSerializer(TokenObtainSerializer):
    """
    Authenticates the user, applies custom lock checks,
    and returns ONLY user metadata. Handles forced password reset
    using a secure one-time token instead of exposing temp password.
    """

    def validate(self, attrs):
        # Call base validation to authenticate user
        data = super().validate(attrs)
        user = self.user

        if user.is_locked:
            raise serializers.ValidationError({
                "code": "ACCOUNT_LOCKED",
                "detail": "Your account has been locked. Please contact your administrator."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "code": "ACCOUNT_INACTIVE",
                "detail": "Your account is inactive. Please contact support."
            })

        if user.force_password_change:
            raise serializers.ValidationError({
                "code": "FORCE_PASSWORD_CHANGE",
                "detail": "You must reset your temporary password before logging in.",
                "email": user.email,
            })

        return {
            "public_id": str(user.public_id),
            "role_id": user.active_role.public_id if user.active_role else None,
        }

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Case-insensitive lookup, but DO NOT raise if missing
        self.user = User.objects.filter(email__iexact=value).first()
        return value

    def save(self):
        # IMPORTANT:
        # If user does not exist → silently succeed
        if not self.user:
            return None

        user = self.user

        token_service = PasswordResetToken()
        event = token_service.generate_token(user_public_id=user.public_id)
        token = event.token

        reset_link = f"{settings.FRONTEND_URL}/password-reset?token={token}"

        try:
            send_mail(
                subject="Password Reset Instructions",
                message=(
                    "You requested a password reset.\n\n"
                    "Your reset link (expires in 10 minutes):\n\n"
                    f"{reset_link}\n\n"
                    "If you did not request this, you can safely ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to send password reset email for user %s", user.public_id)
            # Do NOT leak error details
            raise serializers.ValidationError({"detail": "Could not send password reset email, please try again later."})

        return None
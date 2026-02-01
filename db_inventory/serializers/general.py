from rest_framework import serializers
from db_inventory.models.users import User
from db_inventory.utils.tokens import PasswordResetToken
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
import logging

from db_inventory.tasks import send_password_reset_email

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

    def save(self):
      
        email = self.validated_data["email"]

        # Fire-and-forget
        send_password_reset_email.delay(email)

        return None
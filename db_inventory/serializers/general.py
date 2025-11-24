from rest_framework import serializers
from ..models import  User, UserSession, PasswordResetEvent
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from django.contrib.auth import get_user_model
from ..utils import PasswordResetToken
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta


User = get_user_model()
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
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value
    
    def get_user(self):
        return User.objects.filter(email=self.validated_data["email"]).first()

    def save(self):
        user = self.get_user()

        token = PasswordResetToken.generate_token(user.public_id)

        reset_link = f"{settings.FRONTEND_URL}/password-reset?token={token}"
        send_mail(
                subject="Password Reset Instructions",
                message=f"""
            You requested a password reset. Please use the link below to reset your password. 
            This link will expire in 10 minutes.

            {reset_link}

            If you did not request a password reset, you can safely ignore this email.
            """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )


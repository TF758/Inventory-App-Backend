from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import  User, UserSession
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from .roles import RoleReadSerializer
from django.contrib.auth import get_user_model
from ..utils import PasswordResetToken
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import password_validation
from django.db import transaction

User = get_user_model()

class SessionTokenLoginViewSerializer(TokenObtainSerializer):
    """
    Only authenticates the user and returns metadata.
    Does NOT generate refresh JWTs (we use DB-backed opaque refresh tokens).
    """

    def validate(self, attrs):
        data = super().validate(attrs)  # only authenticates the user

        return {
            "public_id": str(self.user.public_id),
            "role_id": (
                self.user.active_role.public_id if self.user.active_role else None
            ),
        }


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        user = User.objects.get(email=self.validated_data["email"])

        token = PasswordResetToken.generate_token(user.public_id)

        reset_link = f"http://127.0.0.1:8000/api/password-reset/confirm/?token={token}"
        send_mail(
            subject="Password Reset Request",
            message=f"Use the following link to reset your password (valid 10 mins):\n{reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def save(self):
        user_public_id = PasswordResetToken.validate_token(self.validated_data["token"])
        if not user_public_id:
            raise serializers.ValidationError("Invalid or expired token.")

        try:
            user = User.objects.get(public_id=user_public_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        with transaction.atomic():
            user.password = make_password(self.validated_data["new_password"])
            user.save(update_fields=["password"])

            # Revoke all active sessions for security
            UserSession.objects.filter(
                user=user,
                status=UserSession.Status.ACTIVE
            ).update(status=UserSession.Status.REVOKED)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        # check that the user sending it is the current logged in user
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("User not authenticated.")
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        password_validation.validate_password(
            data["new_password"], self.context["request"].user
        )
        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
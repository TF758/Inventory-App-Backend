from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import RoleAssignment, Location, Department, Room, User
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from .roles import RoleReadSerializer
from django.contrib.auth import get_user_model
from ..utils import PasswordResetToken
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings

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
        user = User.objects.get(email=self.validated_data['email'])
        token = PasswordResetToken.generate_token(user.id)
        # TODO: send email
        reset_link = f"http://127.0.0.1:8000/api/password-reset/confirm/?token={token}"
        send_mail(
        subject="Password Reset Request",
        message=f"Use the following link to reset your password (valid 10 mins):\n{reset_link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
        return token

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def save(self):

        user_id = PasswordResetToken.validate_token(self.validated_data['token'])
        if not user_id:
            raise serializers.ValidationError("Invalid or expired token.")

        user = User.objects.get(id=user_id)
        user.password = make_password(self.validated_data['new_password'])
        user.save()
        return user
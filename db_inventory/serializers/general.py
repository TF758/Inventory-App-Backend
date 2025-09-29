from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from ..models import RoleAssignment, Location, Department, Room, User
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from .roles import RoleReadSerializer


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


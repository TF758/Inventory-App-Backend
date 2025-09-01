from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    """Used for validating access tokens and providing additional data to be passed on"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Optional: put safe claims inside the token
        token['public_id'] = str(user.public_id)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Here self.user is your custom user model instance
        data.update({
            "public_id": str(self.user.public_id),
            "fname": self.user.fname,
            "lname": self.user.lname,
        })
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_message = {
        'bad_token': ('Token is expired or invalid')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise serializers.ValidationError(
                {'refresh': self.error_messages['bad_token']}
            )
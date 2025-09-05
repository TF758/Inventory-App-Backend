from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Always include basic user info
        token["public_id"] = str(user.public_id)
        token["fname"] = user.fname
        token["lname"] = user.lname

        if "user_id" in token:
            del token["user_id"]


        # Handle active role logic
        roles = list(user.role_assignments.all())
        if len(roles) == 1:
            token["active_role_id"] = roles[0].id
        else:
            token["active_role_id"] = None

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user info into response
        data.update({
            "public_id": str(self.user.public_id),
            "fname": self.user.fname,
            "lname": self.user.lname,
        })
        

        # Active role logic
        roles = list(self.user.role_assignments.all())
        if len(roles) == 1:
            active_role = roles[0]
            data["active_role_id"] = active_role.id
        else:
            active_role = None
            data["active_role_id"] = None

        # Return all role assignments so frontend can choose
        data["roles"] = [
            {
                "id": r.id,
                "role": r.role,
                "department": r.department_id,
                "location": r.location_id,
                "room": r.room_id,
            }
            for r in roles
        ]

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
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
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

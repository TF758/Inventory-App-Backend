from rest_framework import serializers
from db_inventory.models.security import UserSession



class UserSessionSerializer(serializers.ModelSerializer):
    user_public_id = serializers.UUIDField(source="user.public_id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            "id",
            "user_public_id",
            "user_email",
            "status",
            "created_at",
            "expires_at",
            "absolute_expires_at",
            "last_used_at",
            "ip_address",
            "user_agent",
            "device_name",
            "last_ip_address",
            "is_current",
        ]
        read_only_fields = fields

    def get_is_current(self, obj):
        request = self.context.get("request")

        if not request or not request.auth:
            return False

        session_id = request.auth.get("session_id")

        return str(obj.id) == str(session_id)
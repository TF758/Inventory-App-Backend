from rest_framework import serializers
from django.utils import timezone
from db_inventory.models import PasswordResetEvent
from django.contrib.auth import password_validation

class TempPasswordChangeSerializer(serializers.Serializer):
    temp_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("New password and confirmation do not match.")

        # Verify temp password
        try:
            event = PasswordResetEvent.objects.filter(
                user__email=self.context.get("email"),
                used_at__isnull=True,
                expires_at__gte=timezone.now()
            ).order_by("-created_at").first()
        except PasswordResetEvent.DoesNotExist:
            raise serializers.ValidationError("No active password reset found for this user.")

        import hashlib
        if not event or hashlib.sha256(attrs["temp_password"].encode()).hexdigest() != event.temp_password_hash:
            raise serializers.ValidationError("Invalid or expired temporary password.")

        attrs["reset_event"] = event
        return attrs

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
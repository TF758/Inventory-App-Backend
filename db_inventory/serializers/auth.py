from rest_framework import serializers
from django.utils import timezone
from db_inventory.models import PasswordResetEvent, User, UserSession, PasswordResetEvent, AuditLog
from django.contrib.auth import password_validation
from django.conf import settings
from db_inventory.utils import PasswordResetToken
from django.core.mail import send_mail
from django.db import transaction
from django.contrib.auth.hashers import make_password



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
    


class AdminPasswordResetSerializer(serializers.Serializer):
    user_public_id = serializers.CharField()

    def validate_user_public_id(self, value):
        try:
            self.user = User.objects.get(public_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        
        if self.user.is_locked:
            raise serializers.ValidationError("User account is locked.")
        return value

    def save(self, admin):
        """
        admin is passed from serializer.save(admin=request.user)
        """

        token_service = PasswordResetToken()
        event = token_service.generate_token(
            user_public_id=self.user.public_id,
            admin_public_id=admin.public_id   # <-- YES, we pass it here
        )

        reset_link = f"{settings.FRONTEND_URL}/password-reset?token={event.token}"

        # Send email to the user
        send_mail(
            subject="Your Password Reset Request",
            message=f"""
            An administrator has initiated a password reset for your account.

            Use this link (expires in 10 minutes):
            {reset_link}

            If you did not expect this, contact your administrator immediately.
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
        )

        return reset_link
    

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "code": "PASSWORD_MISMATCH",
                "detail": "Passwords do not match."
            })
        return data

    def save(self):
        token_value = self.validated_data["token"]

        # --- NEW: use your updated token verification ---
        token_service = PasswordResetToken()
        event = token_service.verify_token(token_value)

        if event is None:
            # Could be expired OR invalid → separate logic
            raise serializers.ValidationError({
                "code": "TOKEN_INVALID",
                "detail": "The reset link is invalid or has expired."
            })

        # event is a PasswordResetEvent instance
        user = event.user

        # Additional user checks:
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

        # Update the password
        user.password = make_password(self.validated_data["new_password"])
        user.force_password_change = False
        user.save(update_fields=["password", "force_password_change"])

        # Mark token as used
        event.mark_used()

        # Revoke active sessions
        UserSession.objects.filter(
            user=user, status=UserSession.Status.ACTIVE
        ).update(status=UserSession.Status.REVOKED)

        return user


class AuditLogSerializer(serializers.ModelSerializer):
    # --- Readable FK outputs ---
    department = serializers.StringRelatedField(read_only=True)
    location = serializers.StringRelatedField(read_only=True)
    room = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "public_id",

            # Event info
            "event_type",
            "created_at",
            "user_public_id",
            "user_email",

            # Target object
            "target_model",
            "target_id",
            "target_name",
            "description",
            "metadata",

            # Scope (FK + snapshot values)
            "department",
            "department_name",
            "location",
            "location_name",
            "room",
            "room_name",

            # Technical info
            "ip_address",
            "user_agent",
        ]

        read_only_fields = fields



class AuditLogLightSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = AuditLog
        fields = [
            "public_id",
            "event_type",
            "created_at",
            "user_email",

            # Target info
            "target_model",
            "target_id",
            "target_name",

            # Scope snapshot names (always valid, even if FK deleted)
            "department_name",
            "location_name",
            "room_name",
        ]

        read_only_fields = fields
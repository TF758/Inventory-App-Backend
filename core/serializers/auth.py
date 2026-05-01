from rest_framework import serializers
from django.utils import timezone
from core.models.notifications import Notification
from core.models.security import PasswordResetEvent, SecuritySettings
from core.models.sessions import UserSession
from users.models.users import User
from core.models.audit import AuditLog, SiteNameChangeHistory
from django.contrib.auth import password_validation
from core.utils.tokens import PasswordResetToken
from core.tasks import admin_reset_user_password
from django.db import transaction

class TempPasswordChangeSerializer(serializers.Serializer):
    temp_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("New password and confirmation do not match.")

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
        user.force_password_change = False
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
    

class AdminSetTemporaryPasswordSerializer(serializers.Serializer):
    user_public_id = serializers.CharField()
    temporary_password = serializers.CharField(write_only=True)

    def validate_user_public_id(self, value):
        try:
            self.user = User.objects.get(public_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        if self.user.is_locked:
            raise serializers.ValidationError("User account is locked.")

        return value

    def validate(self, data):
        password_validation.validate_password(data["temporary_password"])
        return data

    def save(self, *, admin):
        user = self.user

        with transaction.atomic():
            # Set temporary password
            user.set_password(self.validated_data["temporary_password"])
            user.force_password_change = True
            user.save(update_fields=["password", "force_password_change"])

            # Revoke all active sessions
            UserSession.objects.filter(
                user=user,
                status=UserSession.Status.ACTIVE,
            ).update(status=UserSession.Status.REVOKED)

        # Audit
        AuditLog.objects.create(
            user=admin,
            user_public_id=admin.public_id,
            user_email=admin.email,
            event_type=AuditLog.Events.ADMIN_RESET_PASSWORD,
            description="Admin set temporary password",
            metadata={"initiated_by_admin": True},
            target_model="User",
            target_id=user.public_id,
            target_name=user.email,
        )

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

    def save(self, *, admin):


        admin_reset_user_password.delay(
            user_public_id=self.user.public_id,
            admin_public_id=admin.public_id,
        )
    

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        token_value = data["token"]

        token_service = PasswordResetToken()
        event, status = token_service.verify_token(token_value)

        if status == "expired":
            raise serializers.ValidationError({
                "code": "TOKEN_EXPIRED",
                "detail": "This reset link has expired. Please request a new one."
            })

        if status != "valid":
            raise serializers.ValidationError({
                "code": "TOKEN_INVALID",
                "detail": "The reset link is invalid."
            })

        user = event.user

        # Store for save()
        self.event = event
        self.user = user

        # Account state checks
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

        # Password match check
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "code": "PASSWORD_MISMATCH",
                "detail": "Passwords do not match."
            })

        # Enforce Django password policy
        password_validation.validate_password(
            data["new_password"],
            user=user
        )

        return data

    def save(self):
        user = self.user
        event = self.event

        with transaction.atomic():
            user.set_password(self.validated_data["new_password"])
            user.force_password_change = False
            user.save(update_fields=["password", "force_password_change"])

            event.mark_used()

            revoked_count = UserSession.objects.filter(
                user=user,
                status=UserSession.Status.ACTIVE
            ).update(status=UserSession.Status.REVOKED)

        view = self.context.get("view")

        if revoked_count and view:
            view.audit(
                event_type=AuditLog.Events.SESSION_REVOKED,
                target=user,
                description="Sessions revoked due to password reset",
                metadata={"count": revoked_count},
            )

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

            "metadata",
        ]

        read_only_fields = fields

class AdminUserDemographicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "fname",
            "lname",
            "job_title",
        ]

    def validate_email(self, value):
        return value.lower()

class SiteNameChangeHistorySerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source="changed_at", read_only=True)

    class Meta:
        model = SiteNameChangeHistory
        fields = [
            "id",
            "site_type",
            "object_public_id",
            "old_name",
            "new_name",
            "reason",
            "user_email",
            "date",
        ]

class SiteNameChangeHistoryListSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source="changed_at", read_only=True)

    class Meta:
        model = SiteNameChangeHistory
        fields = [
            "id",
            "site_type",
            "old_name",
            "new_name",
            "user_email",
            "date",
        ]

class NotificationSerializer(serializers.ModelSerializer):
    entity = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "public_id",
            "type",
            "level",
            "title",
            "message",
            "entity",
            "is_read",
            "created_at",
             "meta",  
        ]

    def get_entity(self, obj):
        if not obj.entity_type or not obj.entity_id:
            return None
        return {
            "type": obj.entity_type,
            "id": obj.entity_id,
        }

class SecuritySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySettings
        fields = [
            "session_idle_minutes",
            "session_absolute_hours",
            "max_concurrent_sessions",
            "lockout_attempts",
            "lockout_duration_minutes",
        ]
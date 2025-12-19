from rest_framework import serializers
from django.utils import timezone

class UserDemographicsSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    email = serializers.EmailField()
    job_title = serializers.CharField(allow_blank=True)
    current_location = serializers.CharField(allow_null=True)
    current_active_role = serializers.CharField(allow_null=True)

class UserLoginStatsSerializer(serializers.Serializer):
    last_login = serializers.DateTimeField(allow_null=True)
    account_status = serializers.DictField()
    active_sessions = serializers.IntegerField()
    revoked_sessions = serializers.IntegerField()
    expired_sessions = serializers.IntegerField()
    date_joined = serializers.DateTimeField()
    login_frequency_last_30_days = serializers.IntegerField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        for field in ['last_login', 'date_joined']:
            if ret[field]:
                dt = timezone.localtime(instance[field])
                ret[field] = dt.strftime("%b %d, %Y %I:%M %p")  # e.g., Dec 13, 2025 08:45 PM
        return ret

class UserRoleSummaryItemSerializer(serializers.Serializer):
    role = serializers.CharField()
    scope = serializers.CharField()
    assigned_date = serializers.DateTimeField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret['assigned_date']:
            dt = timezone.localtime(instance['assigned_date'])
            ret['assigned_date'] = dt.strftime("%b %d, %Y %I:%M %p")
        return ret

class UserAuditSummarySerializer(serializers.Serializer):
    total_audit_logs = serializers.IntegerField()
    event_counts = serializers.DictField(child=serializers.IntegerField())
    most_affected_model = serializers.CharField(allow_null=True)

class UserPasswordEventSummarySerializer(serializers.Serializer):
    total_password_reset_events = serializers.IntegerField()
    active_reset_tokens = serializers.IntegerField()

class UserSummaryReportSerializer(serializers.Serializer):
    demographics = UserDemographicsSerializer(required=False)
    loginStats = UserLoginStatsSerializer(required=False)
    roleSummary = UserRoleSummaryItemSerializer(many=True, required=False)
    auditSummary = UserAuditSummarySerializer(required=False)
    passwordevents = UserPasswordEventSummarySerializer(required=False)


class UserSummaryReportRequestSerializer(serializers.Serializer):
    user = serializers.CharField(
        help_text="User public_id or email address"
    )

    sections = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                "demographics",
                "loginStats",
                "roleSummary",
                "auditSummary",
                "passwordevents",
            ]
        ),
        allow_empty=False,
        help_text="List of report sections to include"
    )

    def validate_user(self, value):
        """
        Basic sanitation. Do NOT leak whether a user exists here.
        Existence check belongs in the view for security reasons.
        """
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Invalid user identifier.")
        return value

    def validate_sections(self, value):
        """
        Enforce uniqueness & predictable ordering.
        """
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate sections are not allowed."
            )

        return value
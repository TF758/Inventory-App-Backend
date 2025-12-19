from rest_framework import serializers
from inventory_metrics.models import (
    DailySystemMetrics,
    DailySecurityMetrics,
    DailyRoleMetrics,
    DailyDepartmentSnapshot,
    DailyLocationSnapshot,
    DailyLoginMetrics,
)

class DailySystemMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySystemMetrics
        fields = "__all__"


class DailySecurityMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySecurityMetrics
        fields = "__all__"


class DailyRoleMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyRoleMetrics
        fields = "__all__"


class DailyDepartmentSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyDepartmentSnapshot
        fields = "__all__"


class DailyLocationSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLocationSnapshot
        fields = "__all__"


class DailyLoginMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLoginMetrics
        fields = "__all__"

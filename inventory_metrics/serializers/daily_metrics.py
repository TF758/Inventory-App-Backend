from rest_framework import serializers
from inventory_metrics.models import (
    DailySystemMetrics,
    DailyDepartmentSnapshot,
)

class DailySystemMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySystemMetrics
        fields = "__all__"

class DailyDepartmentSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyDepartmentSnapshot
        fields = "__all__"

from rest_framework import serializers

from analytics.models.metrics import DailySystemMetrics
from analytics.models.snapshots import DailyDepartmentSnapshot

class DailySystemMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySystemMetrics
        fields = "__all__"

class DailyDepartmentSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyDepartmentSnapshot
        fields = "__all__"

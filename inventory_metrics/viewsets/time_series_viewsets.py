from inventory_metrics.serializers import *
from inventory_metrics.models import *
from inventory_metrics.utils import TimeSeriesViewset
from inventory_metrics.serializers.daily_metrics import *

# TO DO: IMPLEMENT THESE VIEWS TO TRACK DAILY STATS 

class SystemMetricsViewSet(TimeSeriesViewset):
    queryset = DailySystemMetrics.objects.all()
    serializer_class = DailySystemMetricsSerializer


class SecurityMetricsViewSet(TimeSeriesViewset):
    queryset = DailySecurityMetrics.objects.all()
    serializer_class = DailySecurityMetricsSerializer


class LoginMetricsViewSet(TimeSeriesViewset):
    queryset = DailyLoginMetrics.objects.all()
    serializer_class = DailyLoginMetricsSerializer


class RoleMetricsViewSet(TimeSeriesViewset):
    queryset = DailyRoleMetrics.objects.all()
    serializer_class = DailyRoleMetricsSerializer
    date_field = "date"


class DepartmentSnapshotViewSet(TimeSeriesViewset):
    queryset = DailyDepartmentSnapshot.objects.select_related("department").all()
    serializer_class = DailyDepartmentSnapshotSerializer
    date_field = "snapshot_date"


class LocationSnapshotViewSet(TimeSeriesViewset):
    queryset = DailyLocationSnapshot.objects.select_related("location").all()
    serializer_class = DailyLocationSnapshotSerializer
    date_field = "snapshot_date"

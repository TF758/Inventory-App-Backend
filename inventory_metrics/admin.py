from django.contrib import admin

from inventory_metrics.models.reports import ReportJob
from inventory_metrics.models.snapshots import DailyDepartmentSnapshot
from inventory_metrics.models.metrics import DailyAuthMetrics, DailyReturnMetrics,DailySystemMetrics

admin.site.register(ReportJob)

admin.site.register(DailyDepartmentSnapshot)

admin.site.register(DailyReturnMetrics)

admin.site.register(DailySystemMetrics)

admin.site.register(DailyAuthMetrics)
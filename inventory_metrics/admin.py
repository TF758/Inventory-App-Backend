from django.contrib import admin

from inventory_metrics.models.reports import ReportJob
from inventory_metrics.models.snapshots import DailyDepartmentSnapshot
from inventory_metrics.models.metrics import DailyAuthMetrics,DailySystemMetrics

admin.site.register(ReportJob)

admin.site.register(DailyDepartmentSnapshot)

admin.site.register(DailySystemMetrics)

admin.site.register(DailyAuthMetrics)
from django.contrib import admin

from analytics.models.metrics import DailyAuthMetrics, DailyReturnMetrics, DailySystemMetrics
from analytics.models.snapshots import DailyDepartmentSnapshot



admin.site.register(DailyDepartmentSnapshot)

admin.site.register(DailyReturnMetrics)

admin.site.register(DailySystemMetrics)

admin.site.register(DailyAuthMetrics)
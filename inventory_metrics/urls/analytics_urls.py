# inventory_metrics/urls/analytics_urls.py

from django.urls import path
from inventory_metrics.viewsets.analytics import (
    SystemOverviewAnalytics,
)

urlpatterns = [
    path(
        "system/overview/",
        SystemOverviewAnalytics.as_view(),
        name="analytics_system_overview",
    ),
]

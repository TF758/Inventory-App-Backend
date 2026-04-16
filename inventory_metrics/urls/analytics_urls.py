# inventory_metrics/urls/analytics_urls.py

from django.urls import path

from analytics.api.viewsets.analytics import DepartmentOverviewAnalytics, SystemOverviewAnalytics


urlpatterns = [
    path(
        "system/overview/",
        SystemOverviewAnalytics.as_view(),
        name="analytics_system_overview",
    ),
       path(
        "departments/<str:department_id>/overview/",
        DepartmentOverviewAnalytics.as_view(),
        name="analytics_department_overview",
    ),
]

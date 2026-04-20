

from django.urls import path

from analytics.api.viewsets.analytics import DepartmentOverviewAnalytics, SystemOverviewAnalytics


urlpatterns = [
    path(
        "system/",
        SystemOverviewAnalytics.as_view(),
        name="analytics_system_overview",
    ),
       path(
        "departments/<str:department_id>/",
        DepartmentOverviewAnalytics.as_view(),
        name="analytics_department_overview",
    ),
]

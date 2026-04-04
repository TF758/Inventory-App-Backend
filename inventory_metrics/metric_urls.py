from django.urls import include, path

from inventory_metrics.viewsets.admin_metrics_viewset import AdminMetricsOverview, LoginMetricsOverview, ReturnMetricsOverview, RoleAssignmentMetricsOverview, SecurityMetricsOverview, UserMetricsOverview



urlpatterns = [

    path("reports/", include("inventory_metrics.urls.report_urls")),
    path("analytics/", include("inventory_metrics.urls.analytics_urls")),

    path("health/", include("inventory_metrics.urls.health_urls")),

    path("general/", AdminMetricsOverview.as_view() , name="admin_metrics_general"),
    path("login/", LoginMetricsOverview.as_view(), name="admin_metrics_login"),
    path("users/", UserMetricsOverview.as_view(), name="admin_metrics_users"),
    path("security/", SecurityMetricsOverview.as_view(), name="admin_metrics_security"),
    path("returns/", ReturnMetricsOverview.as_view(), name="admin_metrics_returns"),
    path("roles/", RoleAssignmentMetricsOverview.as_view(), name="admin_metrics_roles"),
]
from django.urls import include, path

from inventory_metrics.viewsets.admin_metrics_viewset import AdminMetricsOverview, LoginMetricsOverview, RoleAssignmentMetricsOverview, SecurityMetricsOverview, UserMetricsOverview



urlpatterns = [

    path("reports/", include("inventory_metrics.urls.report_urls")),

    path("general/", AdminMetricsOverview.as_view() , name="admin_metrics_general"),
    path("login/", LoginMetricsOverview.as_view(), name="admin_metrics_login"),
    path("users/", UserMetricsOverview.as_view(), name="admin_metrics_users"),
    path("security/", SecurityMetricsOverview.as_view(), name="admin_metrics_security"),
    path("roles/", RoleAssignmentMetricsOverview.as_view(), name="admin_metrics_roles"),
]
from django.urls import include, path

from analytics.api.viewsets.admin_metrics_viewset import AdminMetricsOverview, LoginMetricsOverview, ReturnMetricsOverview, RoleAssignmentMetricsOverview, SecurityMetricsOverview, UserMetricsOverview


urlpatterns = [

    path("general/", AdminMetricsOverview.as_view() , name="admin_metrics_general"),
    path("login/", LoginMetricsOverview.as_view(), name="admin_metrics_login"),
    path("users/", UserMetricsOverview.as_view(), name="admin_metrics_users"),
    path("security/", SecurityMetricsOverview.as_view(), name="admin_metrics_security"),
    path("returns/", ReturnMetricsOverview.as_view(), name="admin_metrics_returns"),
    path("roles/", RoleAssignmentMetricsOverview.as_view(), name="admin_metrics_roles"),
]
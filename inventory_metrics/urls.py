from django.urls import path
from inventory_metrics.views import *


urlpatterns = [

    path("general/", admin_general_metrics, name="admin_metrics_general"),
    path("login/", login_metrics_overview, name="admin_metrics_login"),
    path("users/", user_metrics_overview, name="admin_metrics_users"),
    path("security/", security_metrics_overview, name="admin_metrics_security"),
    path("roles/", role_assignment_metrics_overview, name="admin_metrics_roles"),
]
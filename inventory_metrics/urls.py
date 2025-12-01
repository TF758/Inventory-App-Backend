from django.urls import path
from inventory_metrics.views import *


urlpatterns = [

    path("general/", admin_general_metrics, name="admin_metrics_general"),
    path("login/", login_metrics_overview, name="admin_metrics_login"),
    path("users/", user_metrics_overview, name="admin_metrics_users"),
    path("security/", security_metrics_overview, name="admin_metrics_security"),
    path("roles/", role_assignment_metrics_overview, name="admin_metrics_roles"),
     path("timeseries/system/", system_metric_timeseries, name="metrics_system_timeseries"),
    path("timeseries/security/", security_metric_timeseries, name="metrics_security_timeseries"),
    path("timeseries/logins/", login_metric_timeseries, name="metrics_login_timeseries"),
    path("timeseries/roles/", role_metric_timeseries, name="metrics_role_timeseries"),
    path("timeseries/departments/", department_metric_timeseries, name="metrics_department_timeseries"),
    path("timeseries/locations/", location_metric_timeseries, name="metrics_location_timeseries"),
]
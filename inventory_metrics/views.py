from django.shortcuts import render
from inventory_metrics.viewsets import admin_metrics_viewset

# Create your views here.
# Site Admin Metrics

admin_general_metrics = admin_metrics_viewset.AdminMetricsOverview.as_view()

# Login metrics
login_metrics_overview = admin_metrics_viewset.LoginMetricsOverview.as_view()

# User metrics
user_metrics_overview = admin_metrics_viewset.UserMetricsOverview.as_view()

# Security metrics
security_metrics_overview = admin_metrics_viewset.SecurityMetricsOverview.as_view()

# Role assignment metrics
role_assignment_metrics_overview = admin_metrics_viewset.RoleAssignmentMetricsOverview.as_view()
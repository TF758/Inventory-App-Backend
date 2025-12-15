from django.shortcuts import render
from inventory_metrics.viewsets import admin_metrics_viewset, time_series_viewsets


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

# Timeseries Viewsets

system_metric_timeseries = time_series_viewsets.SystemMetricsViewSet.as_view({"get": "list"})
security_metric_timeseries = time_series_viewsets.SecurityMetricsViewSet.as_view({"get": "list"})
login_metric_timeseries = time_series_viewsets.LoginMetricsViewSet.as_view({"get": "list"})
role_metric_timeseries = time_series_viewsets.RoleMetricsViewSet.as_view({"get": "list"})
department_metric_timeseries = time_series_viewsets.DepartmentSnapshotViewSet.as_view({"get": "list"})
location_metric_timeseries = time_series_viewsets.LocationSnapshotViewSet.as_view({"get": "list"})


# REPORT VIEWS

from inventory_metrics.viewsets.user_reports import UserSummaryReport
from inventory_metrics.viewsets.site_reports import SiteAssetExcelReportAPIView

user_summary_report = UserSummaryReport.as_view()

site_asset_report = SiteAssetExcelReportAPIView.as_view()
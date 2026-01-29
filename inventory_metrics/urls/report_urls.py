from django.urls import path, include
from inventory_metrics.viewsets.user_reports import UserSummaryReport
from inventory_metrics.viewsets.site_reports import SiteAssetExcelReportAPIView, SiteAuditLogReportAPIView
from inventory_metrics.viewsets.general import DownloadReport
from django.urls import re_path

urlpatterns = [

       path(
        "<str:public_id>/download/",
        DownloadReport.as_view(),
        name="download-report",
    ),
    path('user-summary/', UserSummaryReport.as_view(), name='user-summary-report'),
    path('site-assets/',  SiteAssetExcelReportAPIView.as_view(), name='site-asset-report'),
    path('site-audit-logs/',  SiteAuditLogReportAPIView.as_view(), name='site-audit-log-report'),
]
from django.urls import path, include

from django.urls import re_path

from reporting.api.viewsets.inventory_reports import InventorySummaryReport
from reporting.api.viewsets.asset_reports import AssetHistoryReport
from reporting.api.viewsets.reports import DownloadReport, MyReportJobViewSet, ReportJobAdminViewSet
from reporting.api.viewsets.site_reports import SiteAssetExcelReportAPIView, SiteAuditLogReportAPIView
from reporting.api.viewsets.user_reports import UserAuditHistoryPreview, UserAuditHistoryReport, UserLoginHistoryReport, UserSummaryReport





urlpatterns = [

    # -----------------------------
    # User reports
    # -----------------------------

    path( "self/", MyReportJobViewSet.as_view({ "get": "list", }), name="report-list", ),

    path( "self/<str:public_id>/", MyReportJobViewSet.as_view({ "get": "retrieve", "delete": "destroy", }), name="report-detail", ),

    # -----------------------------
    # Admin reports
    # -----------------------------

    path( "admin/", ReportJobAdminViewSet.as_view({ "get": "list", }), name="admin-report-list", ),

    path( "admin/<str:public_id>/", ReportJobAdminViewSet.as_view({ "get": "retrieve", "delete": "destroy", }), name="admin-report-detail", ),
    # -----------------------------
    # Download report
    # -----------------------------

    path( "<str:public_id>/download/", DownloadReport.as_view(), name="download-report", ),
    # -----------------------------
    # Report generation
    # -----------------------------

    path( "user-summary/", UserSummaryReport.as_view(), name="user-summary-report", ),

    path( "site-assets/", SiteAssetExcelReportAPIView.as_view(), name="site-asset-report", ),

    path( "site-audit-logs/", SiteAuditLogReportAPIView.as_view(), name="site-audit-log-report", ),

    path( "user-audit-history/", UserAuditHistoryReport.as_view(), name="user-audit-history-report", ),
    path( "user-audit-history/preview/", UserAuditHistoryPreview.as_view(), name="user-audit-history-preview", ),
    path("user-login-history/", UserLoginHistoryReport.as_view(), name="user-login-history-report"),
    path("asset-history/", AssetHistoryReport.as_view(), name="asset-history-report"),
    path( "inventory-summary/", InventorySummaryReport.as_view(), name="inventory-summary-report", ),
    
]
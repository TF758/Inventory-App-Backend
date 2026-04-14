from django.urls import path, include
from inventory_metrics.viewsets.asset_reports import AssetHistoryReport
from inventory_metrics.viewsets.user_reports import UserAuditHistoryPreview, UserAuditHistoryReport, UserLoginHistoryReport, UserSummaryReport
from inventory_metrics.viewsets.reports import DownloadReport, MyReportJobViewSet, ReportJobAdminViewSet
from inventory_metrics.viewsets.site_reports import SiteAssetExcelReportAPIView, SiteAssetExcelReportAPIView
from django.urls import re_path



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

    path( "site-audit-logs/", SiteAssetExcelReportAPIView.as_view(), name="site-audit-log-report", ),

    path( "user-audit-history/", UserAuditHistoryReport.as_view(), name="user-audit-history-report", ),
    path( "user-audit-history/preview/", UserAuditHistoryPreview.as_view(), name="user-audit-history-preview", ),
    path("user-login-history/", UserLoginHistoryReport.as_view(), name="user-login-history-report"),
    path("asset-history/", AssetHistoryReport.as_view(), name="asset-history-report"),
    
]
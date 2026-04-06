from django.urls import path

from data_import.views import AssetImportCreateView, ImportErrorReportDownloadView



urlpatterns = [
    path("asset-import/", AssetImportCreateView.as_view(), name="asset-import"),
    path( "asset-import/<str:job_id>/errors/", ImportErrorReportDownloadView.as_view(), name="asset-import-errors", ),
]
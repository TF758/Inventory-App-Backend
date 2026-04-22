from django.urls import path

from data_import.views import AssetImportCancelView, AssetImportCreateView, AssetImportErrorDownloadView, AssetImportStatusView



urlpatterns = [
    path("asset-import/", AssetImportCreateView.as_view(), name="asset-import"),

    path( "asset-import/<str:job_id>/", AssetImportStatusView.as_view(), name="asset-import-status", ),

    path( "asset-import/<str:job_id>/download/", AssetImportErrorDownloadView.as_view(), name="asset-import-download", ),
    path( "asset-import/<str:job_id>/cancel/", AssetImportCancelView.as_view(),
)
]
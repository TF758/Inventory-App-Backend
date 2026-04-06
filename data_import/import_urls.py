from django.urls import path

from data_import.views import AssetImportCreateView



urlpatterns = [
    path("asset-import/", AssetImportCreateView.as_view(), name="asset-import"),
]
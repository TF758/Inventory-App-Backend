from django.urls import path, include

urlpatterns = [
    path("inventory/", include("assignments.urls.inventory_urls")),
    path("returns/", include("assignments.urls.asset_return_urls")),
]
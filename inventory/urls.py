from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # API Documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Core platform endpoints
    path("api/", include("core.api_urls")),

    # Domain endpoints
    path("analytics/", include("analytics.urls.analytics_url")),
    path("assets/", include("assets.urls.asset_urls")),
    path("assignments/", include("assignments.urls.assignment_urls")),
    path("reports/", include("reporting.urls.report_urls")),
    path("sites/", include("sites.urls.site_urls")),
    path("imports/", include("data_import.import_urls")),
    path("users/", include("users.urls.user_and_self_urls")),
    path("roles/", include("users.urls.role_urls")),
]
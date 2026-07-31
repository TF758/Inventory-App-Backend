from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework.permissions import AllowAny, IsAdminUser

from core.health import liveness, readiness

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("health/live/", liveness, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),

    path("admin/", admin.site.urls),

    path("", include("django_prometheus.urls")),

    # Core platform endpoints
    path("api/", include("core.api_urls")),

    # Domain endpoints
    path("analytics/", include("analytics.urls.analytics_url")),
    path("assets/", include("assets.urls.asset_urls")),
    path("access/", include("access.urls")),
    path("agreements/", include("agreements.urls.agreements_urls")),
    path("assignments/", include("assignments.urls.assignment_urls")),
    path("reports/", include("reporting.urls.report_urls")),
    path("sites/", include("sites.urls.site_urls")),
    path("imports/", include("data_import.import_urls")),
    path("users/", include("users.urls.user_and_self_urls")),
    path("roles/", include("users.urls.role_urls")),
]

def api_documentation_urlpatterns():
    if not settings.API_DOCS_ENABLED:
        return []

    docs_permissions = (
        [AllowAny]
        if settings.API_DOCS_PUBLIC
        else [IsAdminUser]
    )

    return [
        path(
            "schema/",
            SpectacularAPIView.as_view(
                permission_classes=docs_permissions,
            ),
            name="schema",
        ),
        path(
            "docs/",
            SpectacularSwaggerView.as_view(
                url_name="schema",
                permission_classes=docs_permissions,
            ),
            name="swagger-ui",
        ),
        path(
            "redoc/",
            SpectacularRedocView.as_view(
                url_name="schema",
                permission_classes=docs_permissions,
            ),
            name="redoc",
        ),
    ]


urlpatterns += api_documentation_urlpatterns()

from django.urls import path, include

urlpatterns = [
    path("overview/", include("analytics.urls.overview_urls")),
    path("health-check/", include("analytics.urls.health_urls")),
    path("metrics/", include("analytics.urls.metric_urls")),
  
]
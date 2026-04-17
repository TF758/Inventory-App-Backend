from django.urls import path, include

urlpatterns = [
    path("overview/", include("analytics.urls.overview")),
    path("health-check/", include("analytics.urls.health_urls")),
  
]
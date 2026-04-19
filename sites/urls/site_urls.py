from django.urls import path, include

urlpatterns = [
    path("departments/", include("sites.urls.department_urls")),
    path("locations/", include("sites.urls.location_urls")),
    path("rooms/", include("sites.urls.room_urls")),
]
from django.urls import path, include

urlpatterns = [
    path("equipment/", include("assets.urls.equipment_urls")),
    path("accessories/", include("assets.urls.accessories_urls")),
    path("components/", include("assets.urls.component_urls")),
    path("consumables/", include("assets.urls.consumables_urls")),
  
]
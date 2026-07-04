from django.urls import include, path
from rest_framework.routers import DefaultRouter

from sites.api.viewsets.option_viewsets import DepartmentOptionViewSet, LocationOptionViewSet, RoomOptionViewSet


router = DefaultRouter()

router.register(
    r"departments",
    DepartmentOptionViewSet,
    basename="department-options",
)

router.register(
    r"locations",
    LocationOptionViewSet,
    basename="location-options",
)

router.register(
    r"rooms",
    RoomOptionViewSet,
    basename="room-options",
)

urlpatterns = [
    path("", include(router.urls)),
]
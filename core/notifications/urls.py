from rest_framework.routers import DefaultRouter

from core.viewsets.audit_viewsets import NotificationViewSet


router = DefaultRouter()
router.register(
    r"notifications",
    NotificationViewSet,
    basename="notification",
)

urlpatterns = router.urls

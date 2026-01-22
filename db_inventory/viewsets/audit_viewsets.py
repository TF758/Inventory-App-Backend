

from rest_framework import viewsets, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.mixins import ListDetailSerializerMixin
from db_inventory.models.audit import AuditLog
from db_inventory.pagination import FlexiblePagination
from db_inventory.serializers.auth import AuditLogLightSerializer, AuditLogSerializer, NotificationSerializer
from db_inventory.filters import AuditLogFilter
from rest_framework.generics import ListAPIView
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

from db_inventory.models.security import Notification

class AuditLogViewSet(
    ListDetailSerializerMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Global, immutable audit log.
    Light serializer for list, heavy serializer for detail.
    """

    queryset = (AuditLog.objects.all().select_related("department", "location", "room"))

    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    list_serializer_class = AuditLogLightSerializer
    detail_serializer_class = AuditLogSerializer

    pagination_class = FlexiblePagination

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AuditLogFilter
    search_fields = ['^user_email', 'user_email']

    ordering_fields = ["created_at"]
    ordering = ["-created_at"]




class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User-facing notification inbox.

    Guarantees:
    - Users only see their own notifications
    - INFO notifications may be auto-marked as read
    - WARNING / CRITICAL require explicit acknowledgment
    - Deletion is soft and level-aware
    """

    serializer_class = NotificationSerializer
    pagination_class = FlexiblePagination
    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    def get_queryset(self):
        return (
            Notification.objects
            .filter(
                recipient=self.request.user,
                is_deleted=False,
            )
            .order_by("-created_at")
        )

    # -------------------------------------------------
    # Unread count (bell badge)
    # -------------------------------------------------

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": count})

    # -------------------------------------------------
    # Auto-read INFO notifications (panel open)
    # -------------------------------------------------

    @action(detail=False, methods=["post"], url_path="mark-info-read")
    def mark_info_read(self, request):
        updated = (
            self.get_queryset()
            .filter(
                level=Notification.Level.INFO,
                is_read=False,
            )
            .update(
                is_read=True,
                read_at=timezone.now(),
            )
        )
        return Response({"marked_read": updated})

    # -------------------------------------------------
    # Explicit read / acknowledge (single notification)
    # -------------------------------------------------

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, public_id=None):
        notification = get_object_or_404(
            self.get_queryset(),
            public_id=public_id,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    # -------------------------------------------------
    # Soft delete notification
    # -------------------------------------------------

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_notification(self, request, public_id=None):
        notification = get_object_or_404(
            self.get_queryset(),
            public_id=public_id,
        )

        if notification.level == Notification.Level.CRITICAL:
            return Response(
                {"detail": "Critical notifications cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            notification.level == Notification.Level.WARNING
            and not notification.is_read
        ):
            return Response(
                {"detail": "Notification must be acknowledged before deletion."},
                status=status.HTTP_403_FORBIDDEN,
            )

        notification.is_deleted = True
        notification.deleted_at = timezone.now()
        notification.save(update_fields=["is_deleted", "deleted_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)
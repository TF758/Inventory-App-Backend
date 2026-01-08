

from rest_framework import viewsets, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.mixins import ListDetailSerializerMixin
from db_inventory.models.audit import AuditLog
from db_inventory.pagination import FlexiblePagination
from db_inventory.serializers.auth import AuditLogLightSerializer, AuditLogSerializer
from db_inventory.filters import AuditLogFilter
from rest_framework.generics import ListAPIView


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

   
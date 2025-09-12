from rest_framework import viewsets
from ..serializers.accessories import (
    AccessoryFullSerializer,
    AccessorySerializer, 
    AccessoryReadSerializer,
    AccessoryWriteSerializer
)
from ..models import Accessory
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import AccessoryFilter
from ..mixins import ScopeFilterMixin


class AccessoryModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Accessory objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Accessory objects."""

    queryset = Accessory.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AccessoryWriteSerializer
        return AccessoryFullSerializer
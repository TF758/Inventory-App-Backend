from rest_framework import viewsets
from ..serializers.equipment import (
EquipmentNameSerializer,
EquipmentReadSerializer,
EquipmentWriteSerializer
)
from ..models import Equipment
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import EquipmentFilter
from ..mixins import ScopeFilterMixin


class EquipmentModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Equipment objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Equipment objects."""

    queryset = Equipment.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    model_class = Equipment

    filterset_class = EquipmentFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EquipmentWriteSerializer
        return EquipmentReadSerializer


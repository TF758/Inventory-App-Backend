from rest_framework import viewsets
from ..serializers.consumables import (
ConsumableReadSerializer,
ConsumableWriteSerializer,
ConsumableSerializer
)
from ..models import Consumable
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import ConsumableFilter


class ConsumableModelViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Consumable objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Consumable objects."""
    
    queryset = Consumable.objects.all()
    serializer_class = ConsumableSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ConsumableWriteSerializer
        return ConsumableReadSerializer
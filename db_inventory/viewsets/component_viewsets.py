from rest_framework import viewsets
from ..serializers.components import (
   ComponentReadSerializer,
   ComponentWriteSerializer
)
from ..models import Component
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import ComponentFilter
from ..mixins import ScopeFilterMixin

class ComponentModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Component objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Component objects."""

    queryset = Component.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ComponentFilter


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ComponentWriteSerializer
        return ComponentReadSerializer
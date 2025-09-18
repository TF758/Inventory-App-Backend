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
from django.db.models import Case, When, Value, IntegerField


class ComponentModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Component objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Component objects."""

    queryset = Component.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    filterset_class = ComponentFilter


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ComponentWriteSerializer
        return ComponentReadSerializer
    

    def get_queryset(self):
        qs = super().get_queryset()
        search_term = self.request.query_params.get('search', None)

        if search_term:
            # Annotate results: 1 if starts with search_term, 2 otherwise
            qs = qs.annotate(
                starts_with_order=Case(
                    When(name__istartswith=search_term, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).order_by('starts_with_order', 'name')  # starts-with results first

        return qs
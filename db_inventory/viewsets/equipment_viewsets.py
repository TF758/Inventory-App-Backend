from rest_framework import viewsets
from ..serializers.equipment import (
EquipmentWriteSerializer
,EquipmentSerializer
)
from ..models import Equipment
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import EquipmentFilter
from ..mixins import ScopeFilterMixin
from django.db.models import Case, When, Value, IntegerField
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.decorators import action
from ..mixins import EquipmentBatchMixin
from django.conf import settings
from ..pagination import FlexiblePagination

class EquipmentModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Equipment objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Equipment objects."""

    queryset = Equipment.objects.all().order_by('-id')
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    model_class = Equipment

    filterset_class = EquipmentFilter

    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EquipmentWriteSerializer
        return EquipmentSerializer
    

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
    
class EquipmentBatchValidateView(EquipmentBatchMixin, APIView):
    """
    Validate a batch of equipment rows without saving.
    """
    save_to_db = False

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, list) else []
        if not data:
            return Response({"detail": "Expected a list of objects"}, status=status.HTTP_400_BAD_REQUEST)

        successes, errors = self.process_batch(data)

        return Response(
            {
                "validated": successes,
                "errors": errors,
                "summary": {
                    "total": len(data),
                    "valid": len(successes),
                    "invalid": len(errors),
                },
            },
            status=status.HTTP_200_OK,
        )


class EquipmentBatchImportView(EquipmentBatchMixin, APIView):
    """
    Batch import of equipment (saves to DB).
    """
    save_to_db = True

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, list) else []
        if not data:
            return Response({"detail": "Expected a list of objects"}, status=status.HTTP_400_BAD_REQUEST)

        successes, errors = self.process_batch(data)

        return Response(
            {
                "created": successes,
                "errors": errors,
                "summary": {
                    "total": len(data),
                    "success": len(successes),
                    "failed": len(errors),
                },
            },
            status=status.HTTP_207_MULTI_STATUS,
        )

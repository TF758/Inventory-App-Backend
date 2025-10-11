from rest_framework import viewsets
from ..serializers.consumables import (
ConsumableWriteSerializer,
ConsumableAreaReaSerializer
)
from ..models import Consumable, Room
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import ConsumableFilter
from ..mixins import ScopeFilterMixin
from django.db.models import Case, When, Value, IntegerField
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from ..pagination import FlexiblePagination
from ..mixins import ConsumableBatchMixin
from ..permissions import AssetPermission, is_in_scope


class ConsumableModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Consumable objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Consumable objects."""
    
    queryset = Consumable.objects.all().order_by('-id')
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]

    filterset_class = ConsumableFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ConsumableWriteSerializer
        return ConsumableAreaReaSerializer
    

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
    
    def perform_create(self, serializer):
        room_id = self.request.data.get("room")
        if not room_id:
            raise PermissionDenied("You must specify a room to create equipment.")
        
        room = Room.objects.filter(pk=room_id).first()
        if not room:
            raise PermissionDenied("Invalid room ID.")

        active_role = getattr(self.request.user, "active_role", None)
        if not active_role:
            raise PermissionDenied("No active role assigned.")

        # Permission check for POST creation scope
        if active_role.role != "SITE_ADMIN" and not is_in_scope(active_role, room=room):
            raise PermissionDenied("You do not have permission to create equipment in this room.")

        serializer.save(room=room)
    

class ConsumableBatchValidateView(ConsumableBatchMixin, APIView):
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
                "summary": {"total": len(data), "valid": len(successes), "invalid": len(errors)},
            },
            status=status.HTTP_200_OK,
        )


class ConsumableBatchImportView(ConsumableBatchMixin, APIView):
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
                "summary": {"total": len(data), "success": len(successes), "failed": len(errors)},
            },
            status=status.HTTP_207_MULTI_STATUS,
        )

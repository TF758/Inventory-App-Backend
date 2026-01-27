from rest_framework import viewsets
from db_inventory.serializers.equipment import (
EquipmentStatusChangeSerializer,
EquipmentWriteSerializer
,EquipmentSerializer
)
from db_inventory.models import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import EquipmentFilter
from db_inventory.mixins import ScopeFilterMixin,EquipmentBatchMixin, AuditMixin
from django.db.models import Case, When, Value, IntegerField
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from db_inventory.pagination import FlexiblePagination
from db_inventory.permissions import AssetPermission, is_in_scope
from django.shortcuts import get_object_or_404
from django.db import transaction
from db_inventory.utils.asset_helpers import equipment_event_from_status
from db_inventory.utils.audit import create_audit_log
from db_inventory.permissions.helpers import can_change_equipment_status

class EquipmentModelViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Equipment objects.
    """

    queryset = Equipment.objects.all().order_by('-id')
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    model_class = Equipment

    filterset_class = EquipmentFilter

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]

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

class EquipmentStatusChangeView(APIView):

    """Dedicated view to update equipment sttaus"""
    permission_classes = [AssetPermission]

    def patch(self, request, public_id):
        serializer = EquipmentStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        equipment = get_object_or_404(Equipment, public_id=public_id)

        self.check_object_permissions(request, equipment)

        old_status = equipment.status

        if old_status == new_status:
            return Response(
                {"detail": "Status is already set to this value."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if not can_change_equipment_status(request.user, equipment, new_status):
            return Response(
                {"detail": "You are not allowed to set this status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            equipment.status = new_status
            equipment.save(update_fields=["status"])

             # Derive domain event
            event_type = equipment_event_from_status(new_status)

            EquipmentEvent.objects.create(
                equipment=equipment,
                user=request.user,
                reported_by=request.user,
                event_type=event_type,
                notes=notes or f"{old_status} → {new_status}",
            )

            create_audit_log(
                request=request,
                event_type=AuditLog.Events.EQUIPMENT_STATUS_CHANGED,
                target=equipment,
                description=f"Status changed from {old_status} to {new_status}",
                metadata={
                    "change_type": "equipment_status_change",
                    "old_status": old_status,
                    "new_status": new_status,
                    "notes": notes,
                },
            )

        return Response(
            {"public_id": equipment.public_id,"status": equipment.status,},
            status=status.HTTP_200_OK,
        )
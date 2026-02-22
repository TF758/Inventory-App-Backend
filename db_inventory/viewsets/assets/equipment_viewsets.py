from rest_framework import viewsets
from db_inventory.serializers.equipment import (
EquipmentCondemnSerializer,
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
from django.utils import timezone
from db_inventory.permissions.assets import CanManageAssetCustody, CanUpdateEquipmentStatus
from db_inventory.serializers.batch_processes import BatchAssignEquipmentSerializer, BatchEquipmentCondemnSerializer, BatchEquipmentPublicIDsSerializer, BatchEquipmentStatusChangeSerializer
from db_inventory.permissions.helpers import can_assign_asset_to_user, get_active_role
from db_inventory.services.equipment_assignment import AssignResult, StatusChangeResult, UnassignResult, assign_equipment, change_equipment_status, condemn_equipment, unassign_equipment
from db_inventory.models.assets import EquipmentStatus

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
    """Dedicated view to update equipment status"""

    permission_classes = [CanUpdateEquipmentStatus]

    def patch(self, request, public_id):
        equipment = get_object_or_404(
            Equipment.objects.select_related("active_assignment"),
            public_id=public_id,
        )

        self.check_object_permissions(request, equipment)

        serializer = EquipmentStatusChangeSerializer(
            data=request.data,
            context={
                "request": request,
                "equipment": equipment,
            },
        )
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        old_status = equipment.status
        if old_status == new_status:
            return Response(
                {"detail": "Status is already set to this value."},
                status=status.HTTP_400_BAD_REQUEST,
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

        return Response( status=status.HTTP_200_OK, )

class EquipmentCondemnView(APIView):
    permission_classes = [CanUpdateEquipmentStatus]

    def patch(self, request, public_id):
        equipment = get_object_or_404(
            Equipment.objects.select_related("active_assignment"),
            public_id=public_id,
        )

        self.check_object_permissions(request, equipment)

        if equipment.status == EquipmentStatus.CONDEMNED:
            return Response(
                {"detail": "Equipment is already condemned."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if equipment.is_assigned:
            return Response(
                {"detail": "Equipment must be unassigned before condemnation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EquipmentCondemnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notes = serializer.validated_data["notes"]

        old_status = equipment.status
        new_status = EquipmentStatus.CONDEMNED

        with transaction.atomic():
            equipment.status = new_status
            equipment.save(update_fields=["status"])

            EquipmentEvent.objects.create(
                equipment=equipment,
                user=request.user,
                reported_by=request.user,
                event_type=EquipmentEvent.Event_Choices.CONDEMNED,
                notes=notes,
            )

            create_audit_log(
                request=request,
                event_type=AuditLog.Events.EQUIPMENT_STATUS_CHANGED,
                target=equipment,
                description=f"Equipment condemned (previous status: {old_status})",
                metadata={
                    "change_type": "equipment_condemned",
                    "old_status": old_status,
                    "new_status": new_status,
                    "notes": notes,
                },
            )

        return Response(status=status.HTTP_200_OK)
    
    
class BatchUnassignEquipmentView(APIView):

    permission_classes = [CanManageAssetCustody]

    def post(self, request):

        serializer = BatchEquipmentPublicIDsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment_public_ids = serializer.validated_data["equipment_public_ids"]
        notes = serializer.validated_data.get("notes", "")
        actor = request.user

        success = skipped = failed = 0

        with transaction.atomic():

            equipment_qs = (
                Equipment.objects
                .select_for_update()
                .filter(public_id__in=equipment_public_ids)
                .order_by("id")
            )

            equipment_map = {e.public_id: e for e in equipment_qs}
            now = timezone.now()

            for public_id in equipment_public_ids:

                equipment = equipment_map.get(public_id)

                if not equipment:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, equipment)

                    result = unassign_equipment(
                        actor=actor,
                        equipment=equipment,
                        notes=notes,
                        now=now,
                        use_atomic=False,
                        lock_equipment=False,
                    )

                    if result == UnassignResult.SUCCESS:
                        success += 1
                    else:
                        skipped += 1

                except ValidationError:
                    skipped += 1
                except Exception:
                    failed += 1

        return Response(
            {"success": success, "skipped": skipped, "failed": failed},
            status=status.HTTP_200_OK,
        )
    

class BatchAssignEquipmentView(APIView):

    permission_classes = [CanManageAssetCustody]

    def post(self, request):

        serializer = BatchAssignEquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment_public_ids = serializer.validated_data["equipment_public_ids"]
        to_user = serializer.validated_data["user_public_id"]
        notes = serializer.validated_data.get("notes", "")
        actor = request.user

        # --- Jurisdiction check ---
        active_role = get_active_role(actor)
        if not can_assign_asset_to_user(active_role, to_user):
            raise ValidationError(
                "You may only assign equipment to users within your jurisdiction."
            )

        success = skipped = failed = 0

        with transaction.atomic():

            equipment_qs = (
                Equipment.objects
                .select_for_update()
                .filter(public_id__in=equipment_public_ids)
                .order_by("id")
            )

            equipment_map = {e.public_id: e for e in equipment_qs}
            now = timezone.now()

            for public_id in equipment_public_ids:

                equipment = equipment_map.get(public_id)

                if not equipment:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, equipment)

                    result = assign_equipment(
                        actor=actor,
                        equipment=equipment,
                        to_user=to_user,
                        notes=notes,
                        now=now,
                        use_atomic=False,
                        lock_equipment=False,
                    )

                    if result == AssignResult.SUCCESS:
                        success += 1
                    else:
                        skipped += 1

                except ValidationError:
                    skipped += 1
                except Exception:
                    failed += 1

        return Response(
            {"success": success, "skipped": skipped, "failed": failed},
            status=status.HTTP_200_OK,
        )
    


class BatchEquipmentStatusChangeView(APIView):

    permission_classes = [CanUpdateEquipmentStatus]

    def post(self, request):
        serializer = BatchEquipmentStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment_public_ids = serializer.validated_data["equipment_public_ids"]
        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        actor = request.user
        now = timezone.now()

        success = skipped = failed = 0

        with transaction.atomic():

            equipment_qs = (
            Equipment.objects
            .select_for_update()
            .filter(public_id__in=equipment_public_ids)
            .order_by("id")
            )

            equipment_map = {e.public_id: e for e in equipment_qs}

            for public_id in equipment_public_ids:

                eq = equipment_map.get(public_id)
                if not eq:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, eq)

                    result = change_equipment_status(
                        actor=actor,
                        equipment=eq,
                        new_status=new_status,
                        notes=notes,
                        now=now,
                        use_atomic=False,
                        lock_equipment=False,
                    )

                    if result == StatusChangeResult.SUCCESS:
                        success += 1
                    else:
                        skipped += 1

                except Exception:
                    failed += 1

        return Response(
            {"success": success, "skipped": skipped, "failed": failed},
            status=status.HTTP_200_OK,
        )

class BatchEquipmentCondemnView(APIView):

    permission_classes = [CanUpdateEquipmentStatus]

    def post(self, request):
        serializer = BatchEquipmentCondemnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment_public_ids = serializer.validated_data["equipment_public_ids"]
        notes = serializer.validated_data["notes"]

        actor = request.user
        now = timezone.now()

        success = skipped = failed = 0

        with transaction.atomic():

            equipment_qs = (
                Equipment.objects
                .select_for_update()
                .filter(public_id__in=equipment_public_ids)
                .order_by("id")
            )

            equipment_map = {e.public_id: e for e in equipment_qs}

            for public_id in equipment_public_ids:

                eq = equipment_map.get(public_id)
                if not eq:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, eq)

                    result = condemn_equipment(
                        actor=actor,
                        equipment=eq,
                        notes=notes,
                        now=now,
                        use_atomic=False,  
                        lock_equipment=False,
                    )

                    if result == StatusChangeResult.SUCCESS:
                        success += 1
                    else:
                        skipped += 1

                except PermissionError:
                    failed += 1

               
        return Response(
            {"success": success, "skipped": skipped, "failed": failed},
            status=status.HTTP_200_OK,
        )
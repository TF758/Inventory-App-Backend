from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from db_inventory.models.users import User
from db_inventory.models.assets import Equipment, EquipmentStatus
from db_inventory.models.asset_assignment import EquipmentAssignment, EquipmentEvent
from db_inventory.models.audit import AuditLog
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from db_inventory.mixins import AuditMixin
from db_inventory.serializers.assignment import AssignEquipmentSerializer, EquipmentEventSerializer, ReassignEquipmentSerializer, UnassignEquipmentSerializer, EquipmentAssignmentSerializer
from db_inventory.permissions.assets import CanManageEquipmentCustody, CanViewEquipmentAssignments
from db_inventory.permissions.helpers import can_assign_equipment_to_user, get_active_role, is_user_in_scope
from rest_framework import mixins, viewsets, filters
from db_inventory.filters import EquipmentAssignmentFilter
from django_filters.rest_framework import DjangoFilterBackend

from db_inventory.pagination import FlexiblePagination

class EquipmentAssignmentViewSet(
    AuditMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset to handle Listing Equipment Assignment
    both via list and in detail used by Site Admin
    """

    queryset = EquipmentAssignment.objects.select_related(
        "equipment", "user", "assigned_by"
    )
    serializer_class = EquipmentAssignmentSerializer
    permission_classes = [CanViewEquipmentAssignments]
    pagination_class = FlexiblePagination

    filterset_class = EquipmentAssignmentFilter

    def get_object(self):
        equipment_public_id = self.kwargs.get("equipment_id")

        obj = get_object_or_404(
            EquipmentAssignment,
            equipment__public_id=equipment_public_id,
        )

        self.check_object_permissions(self.request, obj)
        return obj

class AssignEquipmentView(AuditMixin, APIView):
    """
    Assign an equipment to a user.
    Uses a single mutable EquipmentAssignment per equipment.
    """

    permission_classes = [CanManageEquipmentCustody]

    def post(self, request):
        serializer = AssignEquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignee = serializer.validated_data["user"]
        equipment = serializer.validated_data["equipment"]
        notes = serializer.validated_data.get("notes", "")

        # ASSET AUTHORITY
        self.check_object_permissions(request, equipment)

        # ASSIGNEE JURISDICTION
        active_role = get_active_role(request.user)
        if not can_assign_equipment_to_user(active_role, assignee):
            raise ValidationError(
                "You may only assign equipment to users within your room jurisdiction."
            )

        with transaction.atomic():

            #  Lock the equipment row 
            equipment = (Equipment.objects.select_for_update().get(pk=equipment.pk))

            # Final guard after lock
            if equipment.is_assigned:
                raise ValidationError("This equipment is already assigned")

            # OPTION 1: reuse or mutate assignment row
            assignment, created = EquipmentAssignment.objects.get_or_create(
                equipment=equipment,
                defaults={
                    "user": assignee,
                    "assigned_by": request.user,
                    "notes": notes,
                },
            )

            if not created:
                assignment.user = assignee
                assignment.assigned_by = request.user
                assignment.assigned_at = timezone.now()
                assignment.returned_at = None
                assignment.notes = notes
                assignment.save()
            else:
                assignment.save()

            # Domain event
            EquipmentEvent.objects.create(
                equipment=equipment,
                user=assignee,
                event_type=EquipmentEvent.Event_Choices.ASSIGNED,
                reported_by=request.user,
                notes=notes or "Equipment assigned",
            )

            # Audit log
            self.audit(
                event_type=AuditLog.Events.ASSET_ASSIGNED,
                target=equipment,
                description=f"Equipment assigned to {assignee.email}",
                metadata={
                    "assigned_to": assignee.public_id,
                    "notes": notes,
                },
            )

        return Response(
            {
                "equipment": equipment.public_id,
                "assigned_to": assignee.public_id,
                "assigned_at": assignment.assigned_at,
            },
            status=status.HTTP_201_CREATED,
        )



class UnassignEquipmentView(AuditMixin, APIView):
    """
    Unassign (return) an equipment from a user.
    Uses a single mutable EquipmentAssignment per equipment.
    """

    permission_classes = [CanManageEquipmentCustody]

    def post(self, request):
        serializer = UnassignEquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment = serializer.validated_data["equipment"]
        user = serializer.validated_data["user"]
        notes = serializer.validated_data.get("notes", "")

        # ASSET AUTHORITY
        self.check_object_permissions(request, equipment)

        with transaction.atomic():

            #  Lock equipment row
            equipment = (Equipment.objects.select_for_update().get(pk=equipment.pk))

            # Re-resolve assignment AFTER lock
            assignment = equipment.active_assignment if equipment.is_assigned else None
            if not assignment:
                raise ValidationError("No active assignment found")
            
            if assignment.user != user:
                raise ValidationError("Equipment is not assigned to this user")
            
            # Idempotency guard
            if assignment.returned_at is not None:
                raise ValidationError("This equipment is already unassigned")

            # Close assignment
            assignment.returned_at = timezone.now()
            assignment.save(update_fields=["returned_at"])

            # Domain event
            EquipmentEvent.objects.create(
                equipment=equipment,
                user=user,
                event_type=EquipmentEvent.Event_Choices.RETURNED,
                reported_by=request.user,
                notes=notes or "Equipment returned",
            )

            # Audit log
            self.audit(
                event_type=AuditLog.Events.ASSET_UNASSIGNED,
                target=equipment,
                description=f"Equipment unassigned from {user.email}",
                metadata={
                    "returned_by": user.public_id,
                    "notes": notes,
                },
            )

        return Response(
            {
                "equipment": equipment.public_id,
                "returned_from": user.public_id,
                "returned_at": assignment.returned_at,
            },
            status=status.HTTP_200_OK,
        )


class ReassignEquipmentView(AuditMixin, APIView):
    """
    Reassign equipment from one user to another.
    Uses a single mutable EquipmentAssignment per equipment.
    """

    permission_classes = [CanManageEquipmentCustody]

    def post(self, request):
        serializer = ReassignEquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment = serializer.validated_data["equipment"]
        from_user = serializer.validated_data["from_user"]
        to_user = serializer.validated_data["to_user"]
        notes = serializer.validated_data.get("notes", "")

     
        self.check_object_permissions(request, equipment)

      
        active_role = get_active_role(request.user)
        if not can_assign_equipment_to_user(active_role, to_user):
            raise ValidationError(
                "You may only reassign equipment to users within your room jurisdiction."
            )

        with transaction.atomic():

       
            equipment = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

         
            assignment = equipment.active_assignment if equipment.is_assigned else None
            if not assignment:
                raise ValidationError("No active assignment found")

            # Safety check
            if assignment.user != from_user:
                raise ValidationError(
                    "Equipment is not assigned to from_user"
                )
            if from_user == to_user:
                raise ValidationError("Equipment is already assigned to this user")

            # Domain event: returned from old user
            EquipmentEvent.objects.create(
                equipment=equipment,
                user=from_user,
                event_type=EquipmentEvent.Event_Choices.RETURNED,
                reported_by=request.user,
                notes=notes or "Equipment reassigned",
            )

            # Mutate existing assignment 
            assignment.user = to_user
            assignment.assigned_by = request.user
            assignment.assigned_at = timezone.now()
            assignment.returned_at = None
            assignment.notes = notes
            assignment.save()

            # Domain event: assigned to new user
            EquipmentEvent.objects.create(
                equipment=equipment,
                user=to_user,
                event_type=EquipmentEvent.Event_Choices.ASSIGNED,
                reported_by=request.user,
                notes=notes or "Equipment reassigned",
            )

            # Audit log 
            self.audit(
                event_type=AuditLog.Events.ASSET_REASSIGNED,
                target=equipment,
                description=(
                    f"Equipment reassigned from {from_user.email} "
                    f"to {to_user.email}"
                ),
                metadata={
                    "from_user": from_user.public_id,
                    "to_user": to_user.public_id,
                    "notes": notes,
                },
            )

        return Response(
            {
                "equipment": equipment.public_id,
                "from_user": from_user.public_id,
                "to_user": to_user.public_id,
                "reassigned_at": assignment.assigned_at,
            },
            status=status.HTTP_200_OK,
        )
    
class EquipmentEventHistoryViewset(viewsets.ReadOnlyModelViewSet):
    """
    Full chronological event timeline for a piece of equipment.
    """
    serializer_class = EquipmentEventSerializer
    pagination_class = FlexiblePagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["occurred_at"]
    # most recent first
    ordering = ["-occurred_at"] 

    def get_queryset(self):
        equipment_id = self.kwargs.get("public_id")

        return (
            EquipmentEvent.objects.filter(
                equipment__public_id=equipment_id
            )
            .select_related("user", "reported_by")
        )
        
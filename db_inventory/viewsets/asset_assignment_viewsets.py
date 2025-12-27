from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from db_inventory.models.users import User
from db_inventory.models.assets import Equipment, EquipmentStatus
from db_inventory.models.asset_assignment import EquipmentAssignment, EquipmentEvent
from db_inventory.models.audit import AuditLog
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from db_inventory.mixins import AuditMixin
from db_inventory.serializers.assignment import AssignEquipmentSerializer, UnassignEquipmentSerializer



class AssignEquipmentView(AuditMixin, APIView):
    """
    Assign an equipment to a user.
    """

    def post(self, request):
        serializer = AssignEquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        equipment = serializer.validated_data["equipment"]
        notes = serializer.validated_data.get("notes", "")

        with transaction.atomic():

            # Lock the equipment row
            equipment = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

            # Create assignment
            assignment = EquipmentAssignment.objects.create(
                equipment=equipment,
                user=user,
                assigned_by=request.user,
                notes=notes,
            )

            # Update equipment status
            equipment.status = EquipmentStatus.ASSIGNED
            equipment.save(update_fields=["status"])

            # Domain event
            EquipmentEvent.objects.create(
                equipment=equipment,
                user=user,
                event_type=EquipmentEvent.Event_Choices.ASSIGNED,
                reported_by=request.user,
                notes=notes or "Equipment assigned",
            )

            # Audit log (transaction-safe via mixin)
            self.audit(
                event_type=AuditLog.Events.ASSET_ASSIGNED,
                target=equipment,
                description=f"Equipment assigned to {user.email}",
                metadata={
                    "assigned_to": user.email,
                    "notes": notes,
                },
            )

        return Response(
            {
                "equipment": equipment.public_id,
                "assigned_to": user.public_id,
                "assigned_at": assignment.assigned_at,
            },
            status=status.HTTP_201_CREATED,
        )


class UnassignEquipmentView(AuditMixin, APIView):
    """
    Unassign (return) an equipment from a user.
    """

    def post(self, request):
        serializer = UnassignEquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment = serializer.validated_data["equipment"]
        user = serializer.validated_data["user"]
        assignment = serializer.validated_data["assignment"]
        notes = serializer.validated_data.get("notes", "")

        with transaction.atomic():

            # Lock equipment row
            equipment = (
                Equipment.objects
                .select_for_update()
                .get(pk=equipment.pk)
            )

            # Close assignment
            assignment.returned_at = timezone.now()
            assignment.save(update_fields=["returned_at"])

            # Update equipment status
            equipment.status = EquipmentStatus.AVAILABLE
            equipment.save(update_fields=["status"])

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

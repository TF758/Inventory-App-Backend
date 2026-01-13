from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from db_inventory.models.assets import Accessory
from db_inventory.models.asset_assignment import AccessoryAssignment, AccessoryEvent
from db_inventory.models.audit import AuditLog
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from db_inventory.mixins import AuditMixin
from db_inventory.serializers.assignment import AccessoryEventSerializer, AdminReturnAccessorySerializer, AssignAccessorySerializer, CondemnAccessorySerializer,SelfReturnAccessorySerializer
from db_inventory.permissions.assets import CanManageAssetCustody, CanSelfReturnAsset
from rest_framework import mixins, viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from db_inventory.pagination import FlexiblePagination
from db_inventory.permissions.helpers import can_assign_asset_to_user, get_active_role


class AccessoryEventHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Full chronological event timeline for an accessory.
    """
    serializer_class = AccessoryEventSerializer
    pagination_class = FlexiblePagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["occurred_at"]
    ordering = ["-occurred_at"]

    def get_queryset(self):
        accessory_id = self.kwargs.get("public_id")

        return (
            AccessoryEvent.objects.filter(
                accessory__public_id=accessory_id
            )
            .select_related("user", "reported_by")
        )


class AssignAccessoryView(AuditMixin, APIView):
    permission_classes = [CanManageAssetCustody]

    def post(self, request):
        serializer = AssignAccessorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessory = serializer.validated_data["accessory"]
        user = serializer.validated_data["user"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        # Asset authority check
        self.check_object_permissions(request, accessory)
        role = get_active_role(request.user)
        if not can_assign_asset_to_user(role, user):
            raise ValidationError(
                "You do not have permission to assign assets to this user."
            )


        with transaction.atomic():

            # Lock accessory row to prevent race conditions
            accessory = (
                Accessory.objects
                .select_for_update()
                .get(pk=accessory.pk)
            )

            # Final availability guard (after lock)
            if quantity > accessory.available_quantity:
                raise ValidationError("Not enough accessories available")

            # Enforce ONE active assignment per (accessory, user)
            assignment, created = AccessoryAssignment.objects.get_or_create(
                accessory=accessory,
                user=user,
                returned_at__isnull=True,
                defaults={
                    "quantity": quantity,
                    "assigned_by": request.user,
                },
            )

            if not created:
                assignment.quantity += quantity
                assignment.assigned_by = request.user
                assignment.save(update_fields=["quantity", "assigned_by"])

            # Domain event (inventory-neutral)
            AccessoryEvent.objects.create(
                accessory=accessory,
                user=user,
                event_type="assigned",
                quantity_change=0,
                reported_by=request.user,
                notes=notes or f"Assigned {quantity} units",
            )

            # Audit log
            self.audit(
                event_type=AuditLog.Events.ASSET_ASSIGNED,
                target=accessory,
                description=f"Assigned {quantity} accessory units to {user.email}",
                metadata={
                    "user_public_id": user.public_id,
                    "user_email": user.email,
                    "quantity": quantity,
                    "accessory_public_id": accessory.public_id,
                 
                },
            )

        return Response(
            {
                "accessory": accessory.public_id,
                "user": user.public_id,
                "assigned_quantity": quantity,
                "total_assigned_to_user": assignment.quantity,
            },
            status=status.HTTP_201_CREATED,
        )

class AdminReturnAccessoryView(AuditMixin, APIView):
    permission_classes = [CanManageAssetCustody]

    def post(self, request):
        serializer = AdminReturnAccessorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = serializer.validated_data["assignment"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        # Explicit custody check
        self.check_object_permissions(request, assignment.accessory)

        with transaction.atomic():

            # Lock rows we will mutate
            assignment = (
                AccessoryAssignment.objects
                .select_for_update()
                .get(pk=assignment.pk)
            )

            accessory = (
                Accessory.objects
                .select_for_update()
                .get(pk=assignment.accessory.pk)
            )

            if assignment.returned_at:
                raise ValidationError("This assignment is already closed")

            if quantity > assignment.quantity:
                raise ValidationError("Return exceeds assigned quantity")

            assignment.quantity -= quantity
            if assignment.quantity == 0:
                assignment.returned_at = timezone.now()

            assignment.save()

            AccessoryEvent.objects.create(
                accessory=accessory,
                user=assignment.user,
                event_type="returned",
                quantity_change=0,
                reported_by=request.user,
                notes=notes or f"Returned {quantity} units",
            )

            self.audit(
                event_type=AuditLog.Events.ASSET_RETURNED,
                target=accessory,
                description=(
                    f"Admin returned {quantity} accessory units "
                    f"from {assignment.user.email}"
                ),
                metadata={
                    "quantity": quantity,
                    "affected_user_public_id": assignment.user.public_id,
                    "affected_user_email": assignment.user.email,
                    "accessory_public_id": accessory.public_id,
                    "notes": notes,
                },
            )

        return Response(status=status.HTTP_200_OK)

class CondemnAccessoryView(AuditMixin, APIView):
    permission_classes = [CanManageAssetCustody]

    def post(self, request):
        serializer = CondemnAccessorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessory = serializer.validated_data["accessory"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        self.check_object_permissions(request, accessory)

        with transaction.atomic():

            accessory = (
                Accessory.objects
                .select_for_update()
                .get(pk=accessory.pk)
            )

            if quantity > accessory.available_quantity:
                raise ValidationError("Cannot condemn accessories that are currently assigned")

            accessory.quantity -= quantity
            accessory.save()

            AccessoryEvent.objects.create(
                accessory=accessory,
                event_type="condemned",
                quantity_change=-quantity,
                reported_by=request.user,
                notes=notes,
            )

            self.audit(
                event_type=AuditLog.Events.ASSET_CONDEMNED,
                target=accessory,
                description=f"Condemned {quantity} accessory units",
                metadata={
                    "quantity": quantity,
                    "accessory_public_id": accessory.public_id,
                    "reason": notes,
                },
            )

        return Response(status=status.HTTP_200_OK)

class SelfReturnAccessoryView(AuditMixin, APIView):
    permission_classes = [CanSelfReturnAsset]

    def post(self, request):
        serializer = SelfReturnAccessorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessory = serializer.validated_data["accessory"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        assignment = get_object_or_404(
            AccessoryAssignment,
            accessory=accessory,
            user=request.user,
            returned_at__isnull=True,
        )

        with transaction.atomic():

            assignment = (
                AccessoryAssignment.objects
                .select_for_update()
                .get(pk=assignment.pk)
            )

            accessory = (
                Accessory.objects
                .select_for_update()
                .get(pk=accessory.pk)
            )

            if quantity > assignment.quantity:
                raise ValidationError("Return exceeds assigned quantity")

            assignment.quantity -= quantity
            if assignment.quantity == 0:
                assignment.returned_at = timezone.now()

            assignment.save()

            AccessoryEvent.objects.create(
                accessory=accessory,
                user=request.user,
                event_type="returned",
                quantity_change=0,
                reported_by=request.user,
                notes=notes or "User self-return",
            )
            self.audit(
            event_type=AuditLog.Events.ASSET_RETURNED,
            target=accessory,
            description=f"User self-returned {quantity} accessory units",
            metadata={
                "quantity": quantity,
                "accessory_public_id": accessory.public_id,
            },
        )

        return Response(status=status.HTTP_200_OK)
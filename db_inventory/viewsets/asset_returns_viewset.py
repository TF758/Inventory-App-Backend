
from db_inventory.mixins import AuditMixin
from db_inventory.models.audit import AuditLog
from db_inventory.serializers.returns import AccessoryReturnSerializer, EquipmentReturnRequestSerializer
from db_inventory.services.asset_returns import create_accessory_return_request, create_equipment_return_request
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError

class EquipmentReturnViewSet(AuditMixin, viewsets.ViewSet):
    """
    Allows users to request returns for equipment currently assigned to them.
    """

    permission_classes = [IsAuthenticated]

    def create(self, request):

        serializer = EquipmentReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment_ids = serializer.validated_data["equipment"]
        notes = serializer.validated_data.get("notes", "")

        try:
            return_request = create_equipment_return_request( user=request.user, equipment_public_ids=equipment_ids, notes=notes, )

        except DjangoValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Audit the action
        self.audit(
            AuditLog.Events.ASSET_RETURN_REQUESTED,
            target=return_request,
            description="User submitted equipment return request",
            metadata={
                "equipment_ids": equipment_ids,
                "request_id": return_request.public_id,
            },
        )

        return Response(
            {
                "return_request": return_request.public_id,
                "status": return_request.status,
                "items_created": return_request.items.count(),
            },
            status=status.HTTP_201_CREATED,
        )
    

class AccessoryReturnViewSet(AuditMixin, viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    def create(self, request):

        serializer = AccessoryReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessories = serializer.validated_data["accessories"]
        notes = serializer.validated_data.get("notes", "")

        rr = create_accessory_return_request(
            user=request.user,
            accessory_payload=accessories,
            notes=notes
        )

        self.audit(
            AuditLog.Events.ASSET_RETURN_REQUESTED,
            target=rr,
            description="User submitted accessory return request",
            metadata={
                "items": accessories,
                "request_id": rr.public_id,
            }
        )

        return Response(
            {
                "return_request": rr.public_id,
                "status": rr.status,
                "items_created": rr.items.count()
            },
            status=status.HTTP_201_CREATED
        )
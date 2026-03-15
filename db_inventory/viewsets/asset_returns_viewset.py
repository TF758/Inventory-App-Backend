
from db_inventory.mixins import AuditMixin, ScopeFilterMixin
from db_inventory.models.audit import AuditLog
from db_inventory.serializers.returns import AccessoryReturnSerializer, ConsumableReturnSerializer, EquipmentReturnRequestSerializer, ReturnRequestSerializer
from db_inventory.services.asset_returns import create_accessory_return_request, create_consumable_return_request, create_equipment_return_request
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, OrderingFilter
from django.core.exceptions import ValidationError

from db_inventory.permissions.assets import CanRequestAssetReturn
from db_inventory.filters import AdminReturnRequestFilter, ReturnRequestFilter
from db_inventory.models.asset_assignment import ReturnRequest

class EquipmentReturnViewSet(AuditMixin, viewsets.ViewSet):
    """
    Allows users to request returns for equipment currently assigned to them.
    """

    permission_classes = [IsAuthenticated, CanRequestAssetReturn]

    def create(self, request):

        serializer = EquipmentReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        equipment_ids = serializer.validated_data["equipment"]
        notes = serializer.validated_data.get("notes", "")

        try:
            return_request = create_equipment_return_request( user=request.user, equipment_public_ids=equipment_ids, notes=notes, )

        except ValidationError as e:
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

    permission_classes = [IsAuthenticated, CanRequestAssetReturn]

    def create(self, request):

        serializer = AccessoryReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessories = serializer.validated_data["accessories"]
        notes = serializer.validated_data.get("notes", "")

        try:
            rr = create_accessory_return_request(
                user=request.user,
                accessory_payload=accessories,
                notes=notes
            )

        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST
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


class ConsumableReturnViewSet(AuditMixin, viewsets.ViewSet):
    """
    Allows users to request the return of consumables
    currently issued to them.
    """

    permission_classes = [
        IsAuthenticated,
        CanRequestAssetReturn
    ]

    def create(self, request):

        serializer = ConsumableReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consumables = serializer.validated_data["consumables"]
        notes = serializer.validated_data.get("notes", "")

        try:
            return_request = create_consumable_return_request(
                user=request.user,
                consumable_payload=consumables,
                notes=notes
            )

        except ValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Audit log
        self.audit(
            AuditLog.Events.ASSET_RETURN_REQUESTED,
            target=return_request,
            description="User submitted consumable return request",
            metadata={
                "request_id": return_request.public_id,
                "consumables": consumables
            }
        )

        return Response(
            {
                "return_request": return_request.public_id,
                "status": return_request.status,
                "items_created": return_request.items.count(),
            },
            status=status.HTTP_201_CREATED
        )

class SelfReturnRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows users to view their own return requests.
    """

    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReturnRequestFilter

    def get_queryset(self):

        return (
            ReturnRequest.objects
            .filter(requester=self.request.user)
            .prefetch_related(
                "items",
                "items__equipment_assignment__equipment",
                "items__accessory_assignment__accessory",
                "items__consumable_issue__consumable",
            )
            .distinct()
        )
    
class AdminReturnRequestViewSet(
    ScopeFilterMixin,
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]

    model_class = ReturnRequest

    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
    ]

    filterset_class = AdminReturnRequestFilter

    ordering_fields = [
        "requested_at",
        "processed_at",
        "status",
    ]

    ordering = ["-requested_at"]

    queryset = (
        ReturnRequest.objects
        .select_related(
            "requester",
            "processed_by"
        )
        .prefetch_related(
            "items",
            "items__room",
            "items__room__location",
            "items__room__location__department",
            "items__equipment_assignment__equipment",
            "items__accessory_assignment__accessory",
            "items__consumable_issue__consumable",
        )
    )
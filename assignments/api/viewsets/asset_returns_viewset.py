
from db_inventory.mixins import AuditMixin, NotificationMixin, ScopeFilterMixin
from db_inventory.models.notifications import Notification
from db_inventory.models.audit import AuditLog
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.core.exceptions import ValidationError
from rest_framework.decorators import action
from db_inventory.permissions.assets import CanProcessReturnRequest, CanRequestAssetReturn
from db_inventory.filters import AdminReturnRequestFilter, ReturnRequestFilter
from assignments.models.asset_assignment import ReturnRequest, ReturnRequestItem
from db_inventory.pagination import FlexiblePagination
from assignments.api.serializers.returns import ReturnRequestSerializer
from assignments.services.asset_returns import create_mixed_return_request, approve_return_request, deny_return_request, approve_return_item, deny_return_item
from users.api.serializers.self import MixedAssetReturnSerializer


class MixedAssetReturnViewSet(AuditMixin, viewsets.ViewSet):

    """Send a return request of assets of various types"""

    permission_classes = [IsAuthenticated, CanRequestAssetReturn]

    def create(self, request):

        serializer = MixedAssetReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]
        notes = serializer.validated_data.get("notes", "")

        try:
            rr = create_mixed_return_request(
                user=request.user,
                items_payload=items,
                notes=notes
            )

        except ValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.audit(
            AuditLog.Events.ASSET_RETURN_REQUESTED,
            target=rr,
            description="User submitted mixed asset return request",
            metadata={
                "request_id": rr.public_id,
                "items": items,
            }
        )

        return Response(
            {
                "return_request": rr.public_id,
                "status": rr.status,
                "items_created": len(items),
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
    pagination_class = FlexiblePagination

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
    
class AdminReturnRequestViewSet( ScopeFilterMixin, viewsets.ReadOnlyModelViewSet ):
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FlexiblePagination

    model_class = ReturnRequest

    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

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

    # ---------------------------------------
    # Pending return requests
    # ---------------------------------------
    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                status=ReturnRequest.Status.PENDING
            )
        ).distinct()

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AdminReturnRequestWorkflowViewSet( AuditMixin, NotificationMixin, viewsets.GenericViewSet, ):

    permission_classes = [IsAuthenticated, CanProcessReturnRequest]
    queryset = ReturnRequest.objects.all()
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    # ------------------------------------------------
    # Approve return request
    # ------------------------------------------------

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, public_id=None):

        rr = self.get_object()

        if rr.status != ReturnRequest.Status.PENDING:
            return Response(
                {"detail": "Return request already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rr = approve_return_request(rr, request.user)

        # audit log
        self.audit(
            AuditLog.Events.ASSET_RETURNED,
            target=rr,
            description=f"Return request {rr.public_id} approved",
        )

        # notify requester
        self.notify(
            recipient=rr.requester,
            notif_type=Notification.NotificationType.SYSTEM,
            title="Return Request Approved",
            message="Your asset return request has been approved.",
            entity=rr,
            meta={
                "request_id": rr.public_id,
                "status": "approved",
            },
        )
        return Response({
            "request_id": rr.public_id,
            "status": rr.status
        })

    # ------------------------------------------------
    # Deny return request
    # ------------------------------------------------

    @action(detail=True, methods=["post"], url_path="deny")
    def deny(self, request, public_id=None):

        rr = self.get_object()

        if rr.status != ReturnRequest.Status.PENDING:
            return Response(
                {"detail": "Return request already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "")

        rr = deny_return_request(rr, request.user, reason)

        # audit log
        self.audit(
            AuditLog.Events.ASSET_RETURN_DENIED,
            target=rr,
            description=f"Return request {rr.public_id} denied",
        )

        # notify requester
        self.notify(
            recipient=rr.requester,
            notif_type=Notification.NotificationType.SYSTEM,
            level=Notification.Level.WARNING,
            title="Return Request Denied",
            message = (
                f"Your return request was denied. {reason}"
                if reason
                else "Your return request was denied."
            ),
            entity=rr,
            meta={
                "request_id": rr.public_id,
                "status": "denied",
                "reason": reason,
            },
        )

        return Response({
            "request_id": rr.public_id,
            "status": rr.status
        })
    

    @action(detail=True, methods=["post"], url_path="process")
    def process(self, request, public_id=None):

        rr = self.get_object()

        if rr.status != ReturnRequest.Status.PENDING:
            return Response(
                {"detail": "Return request already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_data = request.data.get("items", [])

        if not items_data:
            return Response(
                {"detail": "No items provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_map = {
            item.public_id: item
            for item in rr.items.all()
        }

        processed = []

        for entry in items_data:

            item_id = entry.get("public_id")
            action = entry.get("action")
            reason = entry.get("reason", "")

            item = items_map.get(item_id)

            if not item:
                return Response(
                    {"detail": f"Item {item_id} not part of this request"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if item.status != ReturnRequestItem.Status.PENDING:
                continue

            if action == "approve":
                approve_return_item(item, request.user)

            elif action == "deny":
                deny_return_item(item, request.user, reason)

            else:
                return Response(
                    {"detail": f"Invalid action for item {item_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            processed.append(item_id)

        rr.refresh_from_db()

        self.audit(
            AuditLog.Events.ASSET_RETURNED,
            target=rr,
            description=f"Return request {rr.public_id} resolved via batch",
            metadata={"processed_items": processed},
        )

        self.notify(
            recipient=rr.requester,
            notif_type=Notification.NotificationType.SYSTEM,
            title="Return Request Updated",
            message="Your return request has been processed.",
            entity=rr,
            meta={
                "request_id": rr.public_id,
                "status": rr.status,
            },
        )

        return Response(
            {
                "request_id": rr.public_id,
                "processed_items": processed,
                "status": rr.status,
            },
            status=status.HTTP_200_OK,
        )

class AdminReturnRequestItemWorkflowViewSet( AuditMixin, NotificationMixin, viewsets.GenericViewSet, ):

    permission_classes = [IsAuthenticated, CanProcessReturnRequest]
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    queryset = (
        ReturnRequestItem.objects
        .select_related(
            "return_request",
            "equipment_assignment__equipment",
            "accessory_assignment__accessory",
            "consumable_issue__consumable",
        )
    )

    # -------------------------------
    # Approve single return item
    # -------------------------------

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, *args, **kwargs):

        item = self.get_object()

        if item.status != ReturnRequestItem.Status.PENDING:
            return Response(
                {"detail": "Return item already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approve_return_item(item, request.user)

        rr = item.return_request

        self.audit(
            AuditLog.Events.ASSET_RETURNED,
            target=item,
            description=f"Return item {item.public_id} approved",
        )

        self.notify(
            recipient=rr.requester,
            notif_type=Notification.NotificationType.SYSTEM,
            title="Return Item Approved",
            message="One of your return items has been approved.",
            entity=rr,
            meta={
                "request_id": rr.public_id,
                "item_id": item.public_id,
                "status": "approved",
            },
        )

        return Response(
            {
                "item_id": item.public_id,
                "status": item.status,
                "request_status": rr.status,
            },
            status=status.HTTP_200_OK,
        )

    # -------------------------------
    # Deny single return item
    # -------------------------------

    @action(detail=True, methods=["post"], url_path="deny")
    def deny(self, request, *args, **kwargs):

        item = self.get_object()

        if item.status != ReturnRequestItem.Status.PENDING:
            return Response(
                {"detail": "Return item already processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "")

        deny_return_item(item, request.user, reason)

        rr = item.return_request

        self.audit(
            AuditLog.Events.ASSET_RETURN_DENIED,
            target=item,
            description=f"Return item {item.public_id} denied",
        )

        self.notify(
            recipient=rr.requester,
            notif_type=Notification.NotificationType.SYSTEM,
            level=Notification.Level.WARNING,
            title="Return Item Denied",
            message="One of your return items was denied.",
            entity=rr,
            meta={
                "request_id": rr.public_id,
                "item_id": item.public_id,
                "status": "denied",
                "reason": reason,
            },
        )

        return Response(
            {
                "item_id": item.public_id,
                "status": item.status,
                "request_status": rr.status,
            },
            status=status.HTTP_200_OK,
        )

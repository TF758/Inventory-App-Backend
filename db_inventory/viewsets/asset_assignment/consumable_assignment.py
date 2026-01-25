from rest_framework.exceptions import ValidationError
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db_inventory.mixins import AuditMixin, NotificationMixin
from db_inventory.models.asset_assignment import ConsumableEvent, ConsumableIssue
from db_inventory.models.assets import Consumable
from db_inventory.models.audit import AuditLog
from db_inventory.permissions.assets import CanManageAssetCustody, CanReportConsumableLoss, CanUseAsset
from db_inventory.serializers.assignment import ConsumableDistributionSerializer, ConsumableEventSerializer, IssueConsumableSerializer, ReportConsumableLossSerializer, RestockConsumableSerializer, ReturnConsumableSerializer, UseConsumableSerializer
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, filters
from db_inventory.pagination import FlexiblePagination
from db_inventory.models.security import Notification
from db_inventory.utils.viewset_helpers import get_admins_responsible_for_room, get_current_room_for_user, get_site_admins


class ConsumableEventHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Full chronological event timeline for a consumable.
    """
    serializer_class = ConsumableEventSerializer
    pagination_class = FlexiblePagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["occurred_at"]
    ordering = ["-occurred_at"]

    def get_queryset(self):
        consumable_id = self.kwargs.get("public_id")

        return (
            ConsumableEvent.objects
            .filter(consumable__public_id=consumable_id)
            .select_related(
                "user",
                "reported_by",
                "issue",
            )
        )

class IssueConsumableView(AuditMixin, NotificationMixin, APIView):
    permission_classes = [CanManageAssetCustody]

    def post(self, request):
        serializer = IssueConsumableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consumable = serializer.validated_data["consumable"]
        user = serializer.validated_data["user"]
        quantity = serializer.validated_data["quantity"]
        purpose = serializer.validated_data.get("purpose", "")
        notes = serializer.validated_data.get("notes", "")

        # Permission check
        self.check_object_permissions(request, consumable)

        with transaction.atomic():

            # Lock consumable row
            consumable = (
                Consumable.objects
                .select_for_update()
                .get(pk=consumable.pk)
            )

            if quantity > consumable.quantity:
                raise ValidationError(
                    "Not enough consumable stock available"
                )

            #Try to find existing open issue
            issue = (
                ConsumableIssue.objects
                .select_for_update()
                .filter(
                    consumable=consumable,
                    user=user,
                    returned_at__isnull=True,
                )
                .first()
            )

            if issue:
                # Merge into existing issue
                issue.quantity += quantity
                issue.issued_quantity += quantity
                issue.save(update_fields=["quantity", "issued_quantity"])
            else:
                # Create new issue
                issue = ConsumableIssue.objects.create(
                    consumable=consumable,
                    user=user,
                    quantity=quantity,
                    issued_quantity=quantity,
                    assigned_by=request.user,
                    purpose=purpose,
                )

            # Reduce global stock
            consumable.quantity -= quantity
            consumable.save(update_fields=["quantity"])

            # Event (inventory-affecting)
            ConsumableEvent.objects.create(
                consumable=consumable,
                issue=issue,
                user=user,
                event_type=ConsumableEvent.EventType.ISSUED,
                quantity=quantity,
                quantity_change=-quantity,
                reported_by=request.user,
                notes=notes or f"Issued {quantity} units",
            )

            # Audit log
            self.audit(
                event_type=AuditLog.Events.CONSUMABLE_ISSUED,
                target=consumable,
                description=(
                    f"Issued {quantity} units of {consumable.name} "
                    f"to {user.email}"
                ),
                metadata={
                    "consumable_public_id": consumable.public_id,
                    "user_public_id": user.public_id,
                    "quantity": quantity,
                    "purpose": purpose,
                },
            )

            self.notify(
                recipient=user,
                notif_type=AuditLog.Events.CONSUMABLE_ISSUED,
                level=Notification.Level.INFO,
                title="Consumable issued to you",
                message=(
                    f"{quantity} unit(s) of {consumable.name} "
                    f"were issued to you by {request.user.get_full_name()}."
                ),
                entity=consumable,
                actor=request.user,
            )

        return Response(
            status=status.HTTP_200_OK,
        )

class UseConsumableView(AuditMixin, APIView):
    permission_classes = [CanUseAsset]

    def post(self, request):
        serializer = UseConsumableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consumable = serializer.validated_data["consumable"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        with transaction.atomic():
            # Find an active issue for this user + consumable
            issue = get_object_or_404(
                ConsumableIssue.objects.select_for_update(),
                consumable=consumable,
                user=request.user,
                returned_at__isnull=True,
            )

            if quantity > issue.quantity:
                raise ValidationError(
                    "Usage quantity exceeds your issued consumable quantity."
                )


            # Reduce remaining quantity
            issue.quantity -= quantity
            if issue.quantity == 0:
                issue.returned_at = timezone.now()

            issue.save(update_fields=["quantity", "returned_at"])

            # Record usage event (inventory already accounted for)
            ConsumableEvent.objects.create(
                consumable=consumable,
                issue=issue,
                user=request.user,
                event_type=ConsumableEvent.EventType.USED,
                quantity=quantity,
                quantity_change=-quantity,
                reported_by=request.user,
                notes=notes or f"Used {quantity} units",
            )

            # Audit log
            self.audit(
                event_type=AuditLog.Events.CONSUMABLE_USED,
                target=consumable,
                description=(
                    f"{request.user.email} used "
                    f"{quantity} units of {consumable.name}"
                ),
                metadata={
                    "consumable_public_id": consumable.public_id,
                    "user_public_id": request.user.public_id,
                    "quantity": quantity,
                },
            )

        return Response(
            status=status.HTTP_200_OK,
        )

class AdminReturnConsumableView(AuditMixin,NotificationMixin, APIView):
    permission_classes = [CanManageAssetCustody]

    def post(self, request):
        serializer = ReturnConsumableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        issue = serializer.validated_data["issue"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        consumable = issue.consumable

        # Permission check on the asset itself
        self.check_object_permissions(request, consumable)

        with transaction.atomic():

            # Lock rows
            issue = (
                ConsumableIssue.objects
                .select_for_update()
                .get(pk=issue.pk)
            )

            consumable = (
                Consumable.objects
                .select_for_update()
                .get(pk=consumable.pk)
            )

            if issue.returned_at:
                raise ValidationError("This consumable issue is already closed")

            if quantity > issue.quantity:
                raise ValidationError(
                    "Return quantity exceeds remaining issued quantity"
                )

            # Reduce custody
            issue.quantity -= quantity
            if issue.quantity == 0:
                issue.returned_at = timezone.now()

            issue.save(update_fields=["quantity", "returned_at"])

            # Increase global stock
            consumable.quantity += quantity
            consumable.save(update_fields=["quantity"])

            # Event (inventory-affecting)
            ConsumableEvent.objects.create(
                consumable=consumable,
                issue=issue,
                user=issue.user,
                event_type=ConsumableEvent.EventType.RETURNED,
                quantity=quantity,
                quantity_change=quantity,
                reported_by=request.user,
                notes=notes or f"Returned {quantity} units",
            )

            # Audit
            self.audit(
                event_type=AuditLog.Events.CONSUMABLE_RETURNED,
                target=consumable,
                description=(
                    f"Returned {quantity} units of {consumable.name} "
                    f"from {issue.user.email}"
                ),
                metadata={
                    "consumable_public_id": consumable.public_id,
                    "user_public_id": issue.user.public_id,
                    "quantity": quantity,
                    "issue_id": issue.id,
                    "notes": notes,
                },
            )

            self.notify(
                recipient=issue.user,
                notif_type=AuditLog.Events.CONSUMABLE_RETURNED,
                level=Notification.Level.WARNING,
                title="Consumable returned by admin",
                message=(
                    f"{quantity} unit(s) of {consumable.name} "
                    f"were returned by an administrator."
                ),
                entity=consumable,
                actor=request.user,
            )

        return Response(status=status.HTTP_200_OK,)
    
class ReportConsumableLossView(AuditMixin, NotificationMixin, APIView):
    permission_classes = [CanReportConsumableLoss]

    ALLOWED_EVENT_TYPES = {
        ConsumableEvent.EventType.LOST,
        ConsumableEvent.EventType.DAMAGED,
        ConsumableEvent.EventType.EXPIRED,
        ConsumableEvent.EventType.CONDEMNED,
    }

    def post(self, request):
        serializer = ReportConsumableLossSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

 
        quantity = serializer.validated_data["quantity"]
        event_type = serializer.validated_data["event_type"]
        notes = serializer.validated_data.get("notes", "")

        with transaction.atomic():

            issue = serializer.validated_data.get("issue")

            if issue:
                # 🛡 Admin path (explicit issue)
                issue = (
                    ConsumableIssue.objects
                    .select_for_update()
                    .get(pk=issue.pk)
                )
                consumable = issue.consumable
                self.check_object_permissions(request, consumable)

            else:
                # User self-report path
                consumable = serializer.validated_data["consumable"]
                issue = get_object_or_404(
                    ConsumableIssue.objects.select_for_update(),
                    consumable=consumable,
                    user=request.user,
                    returned_at__isnull=True,
                )

            if issue.returned_at:
                raise ValidationError("This consumable issue is already closed.")

            if quantity > issue.quantity:
                raise ValidationError(
                    "Reported quantity exceeds remaining issued quantity."
                )

            # Reduce custody
            issue.quantity -= quantity
            if issue.quantity == 0:
                issue.returned_at = timezone.now()

            issue.save(update_fields=["quantity", "returned_at"])

            # Record incident event (permanent loss)
            ConsumableEvent.objects.create(
                consumable=issue.consumable,
                issue=issue,
                user=issue.user,            
                event_type=event_type,
                quantity=quantity,
                quantity_change=-quantity,
                reported_by=request.user,     
                notes=notes or f"Reported {event_type} of {quantity} units",
            )
            # Audit log
            self.audit(
                event_type=AuditLog.Events.CONSUMABLE_LOSS_REPORTED,
                target=consumable,
                description=(
                    f"{request.user.email} reported "
                    f"{event_type} of {quantity} units "
                    f"for {consumable.name}"
                ),
             metadata={
                    "consumable_public_id": consumable.public_id,
                    "custody_user_public_id": issue.user.public_id,
                    "custody_user_email_snapshot": issue.user.email,
                    "reported_by_public_id": request.user.public_id,
                    "reported_by_email_snapshot": request.user.email,
                    "quantity": quantity,
                    "event_type": event_type,
                    "notes": notes,
                }
            )

            is_self_report = issue and request.user == issue.user

            if is_self_report:
                user_location = get_current_room_for_user(issue.user)

                admins = (
                    get_admins_responsible_for_room(user_location.room)
                    if user_location and user_location.room
                    else get_site_admins()
                )

                for admin in admins:
                    self.notify(
                        recipient=admin,
                        notif_type=AuditLog.Events.CONSUMABLE_LOSS_REPORTED,
                        level=Notification.Level.CRITICAL,
                        title="Consumable loss reported",
                        message=(
                            f"{issue.user.email} reported {event_type.upper()} "
                            f"of {quantity} unit(s) of {consumable.name}"
                            + (
                                f" in room {user_location.room.name}."
                                if user_location and user_location.room
                                else "."
                            )
                        ),
                        entity=consumable,
                        actor=request.user,
                    )

        return Response(status=status.HTTP_200_OK)

class ConsumableDistributionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Current distribution of a consumable:
    who holds it and how much remains.
    """
    serializer_class = ConsumableDistributionSerializer
    pagination_class = FlexiblePagination
    permission_classes = [CanManageAssetCustody]

    def get_queryset(self):
        consumable_id = self.kwargs.get("public_id")

        return (
            ConsumableIssue.objects
            .filter(
                consumable__public_id=consumable_id,
                returned_at__isnull=True,
                quantity__gt=0,
            )
            .select_related("user", "consumable")
            .order_by("-assigned_at")
        )

class RestockConsumableView(AuditMixin, APIView):
    permission_classes = [CanManageAssetCustody]

    def post(self, request):
        serializer = RestockConsumableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consumable = serializer.validated_data["consumable"]
        quantity = serializer.validated_data["quantity"]
        notes = serializer.validated_data.get("notes", "")

        self.check_object_permissions(request, consumable)

        with transaction.atomic():
            consumable = (
                Consumable.objects
                .select_for_update()
                .get(pk=consumable.pk)
            )

            # Increase global stock
            consumable.quantity += quantity
            consumable.save(update_fields=["quantity"])

            # Inventory-affecting event
            ConsumableEvent.objects.create(
                consumable=consumable,
                event_type=ConsumableEvent.EventType.RESTOCKED,
                quantity=quantity,
                quantity_change=quantity,
                reported_by=request.user,
                notes=notes or f"Restocked {quantity} units",
            )

            # Audit log
            self.audit(
                event_type=AuditLog.Events.ASSET_RESTOCKED,
                target=consumable,
                description=f"Restocked {quantity} units of {consumable.name}",
                metadata={
                    "consumable_public_id": consumable.public_id,
                    "quantity": quantity,
                    "notes": notes,
                },
            )

        return Response(status=status.HTTP_200_OK)
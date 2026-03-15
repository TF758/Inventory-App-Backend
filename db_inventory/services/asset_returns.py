from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from db_inventory.models.asset_assignment import AccessoryAssignment, AccessoryEvent, ConsumableEvent, ConsumableIssue, EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem

@transaction.atomic
def create_equipment_return_request(user, equipment_public_ids, notes=""):

    MAX_EQUIPMENT_PER_RETURN = 20

    if len(equipment_public_ids) > MAX_EQUIPMENT_PER_RETURN:
        raise ValidationError(
            f"Maximum {MAX_EQUIPMENT_PER_RETURN} equipment allowed per return request."
        )

    assignments = (
        EquipmentAssignment.objects
        .select_related("equipment")
        .filter(
            equipment__public_id__in=equipment_public_ids,
            returned_at__isnull=True,
            user=user
        )
    )

    if assignments.count() != len(equipment_public_ids):
        raise ValidationError(
            "Some equipment are not assigned to the user or already returned."
        )

    request = ReturnRequest.objects.create(
        requester=user,
        notes=notes
    )

    items = []

    for assignment in assignments:

        exists = ReturnRequestItem.objects.filter(
            equipment_assignment=assignment,
            return_request__status=ReturnRequest.Status.PENDING
        ).exists()

        if exists:
            raise ValidationError(
                f"{assignment.equipment.public_id} already has a pending return request"
            )

        equipment = assignment.equipment

        items.append(
            ReturnRequestItem(
                return_request=request,
                item_type="equipment",
                equipment_assignment=assignment
            )
        )

        # Equipment timeline event
        EquipmentEvent.objects.create(
            equipment=equipment,
            user=user,
            event_type="return_requested",
            reported_by=user,
            notes=notes
        )

    ReturnRequestItem.objects.bulk_create(items)

    return request
@transaction.atomic
def create_accessory_return_request(user, accessory_payload, notes=""):

    MAX_ASSET_PAYLOAD = 20

    if len(accessory_payload) > MAX_ASSET_PAYLOAD:
        raise ValidationError(
            f"Maximum {MAX_ASSET_PAYLOAD} Accessories allowed per return request."
        )

    request = ReturnRequest.objects.create(
        requester=user,
        notes=notes
    )

    items = []

    for entry in accessory_payload:

        accessory_id = entry["id"]
        quantity = entry["quantity"]

        try:
            assignment = (
                AccessoryAssignment.objects
                .select_related("accessory")
                .get(
                    accessory__public_id=accessory_id,
                    user=user
                )
            )

        except AccessoryAssignment.DoesNotExist:
            raise ValidationError(
                f"{accessory_id} is not assigned to this user."
            )

        if quantity > assignment.quantity:
            raise ValidationError(
                f"Cannot return more than assigned quantity for {accessory_id}"
            )


        exists = ReturnRequestItem.objects.filter(
            accessory_assignment=assignment,
            return_request__status=ReturnRequest.Status.PENDING
        ).exists()

        if exists:
            raise ValidationError(
                f"{accessory_id} already has a pending return request"
            )

        accessory = assignment.accessory

        items.append(
            ReturnRequestItem(
                return_request=request,
                item_type="accessory",
                accessory_assignment=assignment,
                quantity=quantity
            )
        )

        # Timeline event
        AccessoryEvent.objects.create(
            accessory=accessory,
            user=user,
            quantity=quantity,
            quantity_change=0,  # inventory not changed yet
            event_type="return_requested",
            reported_by=user,
            notes=notes,
        )

    ReturnRequestItem.objects.bulk_create(items)

    return request

@transaction.atomic
def create_consumable_return_request(user, consumable_payload, notes=""):

    if len(consumable_payload) > 20:
        raise ValidationError(
            "Maximum 20 consumables can be returned per request."
        )

    request = ReturnRequest.objects.create(
        requester=user,
        notes=notes
    )

    items = []

    for entry in consumable_payload:

        consumable_id = entry["id"]
        quantity = entry["quantity"]

        try:
            issue = (
                ConsumableIssue.objects
                .select_related("consumable")
                .get(
                    consumable__public_id=consumable_id,
                    user=user
                )
            )
        except ConsumableIssue.DoesNotExist:
            raise ValidationError(
                f"{consumable_id} is not issued to this user."
            )

        if quantity > issue.quantity:
            raise ValidationError(
                f"Cannot return more than remaining quantity for {consumable_id}"
            )

        # Prevent duplicate pending return
        exists = ReturnRequestItem.objects.filter(
            consumable_issue=issue,
            return_request__status=ReturnRequest.Status.PENDING
        ).exists()

        if exists:
            raise ValidationError(
                f"{consumable_id} already has a pending return request"
            )

        consumable = issue.consumable

        items.append(
            ReturnRequestItem(
                return_request=request,
                item_type="consumable",
                consumable_issue=issue,
                quantity=quantity
            )
        )

        # Timeline event
        ConsumableEvent.objects.create(
            consumable=consumable,
            issue=issue,
            user=user,
            quantity=quantity,
            quantity_change=0,  # inventory unchanged yet
            event_type="return_requested",
            reported_by=user,
            notes=notes
        )

    ReturnRequestItem.objects.bulk_create(items)

    return request

@transaction.atomic
def approve_return_request(request, admin_user):

    if request.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    now = timezone.now()

    for item in request.items.select_related(
        "equipment_assignment__equipment",
        "accessory_assignment__accessory",
        "consumable_issue__consumable"
    ):

        # -----------------------------
        # Equipment
        # -----------------------------
        if item.item_type == "equipment":

            assignment = item.equipment_assignment
            equipment = assignment.equipment

            assignment.returned_at = now
            assignment.save(update_fields=["returned_at"])

            equipment.status = "AVAILABLE"
            equipment.save(update_fields=["status"])

            EquipmentEvent.objects.create(
                equipment=equipment,
                user=assignment.user,
                event_type=EquipmentEvent.Event_Choices.RETURNED,
                reported_by=admin_user,
            )

        # -----------------------------
        # Accessories
        # -----------------------------
        elif item.item_type == "accessory":

            assignment = item.accessory_assignment
            accessory = assignment.accessory
            returned_qty = item.quantity

            assignment.quantity -= returned_qty
            assignment.save(update_fields=["quantity"])

            accessory.quantity += returned_qty
            accessory.save(update_fields=["quantity"])

            AccessoryEvent.objects.create(
                accessory=accessory,
                user=assignment.user,
                quantity=returned_qty,
                quantity_change=returned_qty,
                event_type=AccessoryEvent.EventType.RETURNED,
                reported_by=admin_user,
            )

        # -----------------------------
        # Consumables
        # -----------------------------
        elif item.item_type == "consumable":

            issue = item.consumable_issue
            consumable = issue.consumable
            returned_qty = item.quantity

            issue.quantity -= returned_qty
            issue.save(update_fields=["quantity"])

            consumable.quantity += returned_qty
            consumable.save(update_fields=["quantity"])

            ConsumableEvent.objects.create(
                consumable=consumable,
                issue=issue,
                user=issue.user,
                quantity=returned_qty,
                quantity_change=returned_qty,
                event_type=ConsumableEvent.EventType.RETURNED,
                reported_by=admin_user,
            )

        # -----------------------------
        # Verification metadata
        # -----------------------------
        item.verified_by = admin_user
        item.verified_at = now
        item.save(update_fields=["verified_by", "verified_at"])

    request.status = ReturnRequest.Status.APPROVED
    request.processed_by = admin_user
    request.processed_at = now

    request.save(update_fields=[
        "status",
        "processed_by",
        "processed_at"
    ])

def deny_return_request(request, admin_user, reason=""):

    if request.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    now = timezone.now()

    request.status = ReturnRequest.Status.DENIED
    request.processed_by = admin_user
    request.processed_at = now
    request.notes = reason

    request.save(update_fields=[
        "status",
        "processed_by",
        "processed_at",
        "notes"
    ])
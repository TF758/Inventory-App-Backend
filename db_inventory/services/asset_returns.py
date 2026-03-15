from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from db_inventory.models.asset_assignment import AccessoryAssignment, AccessoryEvent, ConsumableEvent, ConsumableIssue, EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem
from db_inventory.models.assets import Accessory, Consumable, EquipmentStatus

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
                equipment_assignment=assignment,
                room = assignment.equipment.room
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

        accessory_id = entry["accessory_public_id"]
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
                quantity=quantity,
                room = assignment.accessory.room
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

        consumable_id = entry["consumable_public_id"]
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
                quantity=quantity,
                room = issue.consumable.room
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
def approve_return_request(return_request, admin_user):

    rr = (
        ReturnRequest.objects
        .select_for_update()
        .prefetch_related("items")
        .get(pk=return_request.pk)
    )

    if rr.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    now = timezone.now()

    assignments_to_update = []
    accessories_to_update = []
    consumables_to_update = []
    items_to_update = []

    equipment_events = []
    accessory_events = []
    consumable_events = []

    items = rr.items.select_related(
        "equipment_assignment__equipment",
        "accessory_assignment__accessory",
        "consumable_issue__consumable"
    )

    for item in items:

        # Equipment
        if item.item_type == "equipment":

            assignment = item.equipment_assignment
            equipment = assignment.equipment

            assignment.returned_at = now
            assignments_to_update.append(assignment)

            equipment_events.append(
                EquipmentEvent(
                    equipment=equipment,
                    user=assignment.user,
                    event_type=EquipmentEvent.Event_Choices.RETURNED,
                    reported_by=admin_user,
                )
            )

        # Accessory
        elif item.item_type == "accessory":

            assignment = item.accessory_assignment
            accessory = assignment.accessory
            returned_qty = item.quantity

            assignment.quantity -= returned_qty
            accessory.quantity += returned_qty

            assignments_to_update.append(assignment)
            accessories_to_update.append(accessory)

            accessory_events.append(
                AccessoryEvent(
                    accessory=accessory,
                    user=assignment.user,
                    quantity=returned_qty,
                    quantity_change=returned_qty,
                    event_type=AccessoryEvent.EventType.RETURNED,
                    reported_by=admin_user,
                )
            )

        # Consumable
        elif item.item_type == "consumable":

            issue = item.consumable_issue
            consumable = issue.consumable
            returned_qty = item.quantity

            issue.quantity -= returned_qty
            consumable.quantity += returned_qty

            assignments_to_update.append(issue)
            consumables_to_update.append(consumable)

            consumable_events.append(
                ConsumableEvent(
                    consumable=consumable,
                    issue=issue,
                    user=issue.user,
                    quantity=returned_qty,
                    quantity_change=returned_qty,
                    event_type=ConsumableEvent.EventType.RETURNED,
                    reported_by=admin_user,
                )
            )

        item.verified_by = admin_user
        item.verified_at = now
        items_to_update.append(item)

    # Batch updates
    EquipmentAssignment.objects.bulk_update(assignments_to_update, ["returned_at", "quantity"])
    Accessory.objects.bulk_update(accessories_to_update, ["quantity"])
    Consumable.objects.bulk_update(consumables_to_update, ["quantity"])
    ReturnRequestItem.objects.bulk_update(items_to_update, ["verified_by", "verified_at"])

    # Batch event creation
    EquipmentEvent.objects.bulk_create(equipment_events)
    AccessoryEvent.objects.bulk_create(accessory_events)
    ConsumableEvent.objects.bulk_create(consumable_events)

    rr.status = ReturnRequest.Status.APPROVED
    rr.processed_by = admin_user
    rr.processed_at = now
    rr.save(update_fields=["status", "processed_by", "processed_at"])


@transaction.atomic
def deny_return_request(return_request, admin_user, reason=""):

    rr = (
        ReturnRequest.objects
        .select_for_update()
        .get(pk=return_request.pk)
    )

    if rr.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    now = timezone.now()

    rr.status = ReturnRequest.Status.DENIED
    rr.processed_by = admin_user
    rr.processed_at = now
    rr.notes = reason

    rr.save(update_fields=[
        "status",
        "processed_by",
        "processed_at",
        "notes",
    ])

    return rr
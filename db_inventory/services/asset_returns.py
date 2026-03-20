from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from db_inventory.models.asset_assignment import AccessoryAssignment, AccessoryEvent, ConsumableEvent, ConsumableIssue, EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem
from db_inventory.models.base import generate_public_id
from db_inventory.utils.query_helpers import get_user_accessories, get_user_consumables
from db_inventory.services.asset_return_builders import build_accessory_return_items, build_consumable_return_items, build_equipment_return_items

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

        item = ReturnRequestItem(
                return_request=request,
                item_type="equipment",
                equipment_assignment=assignment,
                room = assignment.equipment.room
            )
        
        item.public_id = generate_public_id("RRI")  # <-- ADD THIS
        items.append(item)

        # Equipment timeline event
        EquipmentEvent.objects.create(
            equipment=equipment,
            user=user,
            event_type=EquipmentEvent.Event_Choices.RETURN_REQUESTED,
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
            f"Maximum {MAX_ASSET_PAYLOAD} accessories allowed per return request."
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
                get_user_accessories(user)
                .select_related("accessory")
                .get(accessory__public_id=accessory_id)
            )
        except AccessoryAssignment.DoesNotExist:
            raise ValidationError(
                f"{accessory_id} is not assigned to this user."
            )

        # Ensure user cannot return more than assigned
        if quantity > assignment.quantity:
            raise ValidationError(
                f"Cannot return more than assigned quantity for {accessory_id}"
            )

        # Prevent duplicate pending return requests
        exists = ReturnRequestItem.objects.filter(
            accessory_assignment=assignment,
            return_request__status=ReturnRequest.Status.PENDING
        ).exists()

        if exists:
            raise ValidationError(
                f"{accessory_id} already has a pending return request"
            )

        accessory = assignment.accessory

        item = ReturnRequestItem(
            return_request=request,
            item_type="accessory",
            accessory_assignment=assignment,
            quantity=quantity,
            room=accessory.room
        )

        item.public_id = generate_public_id("RRI")
        items.append(item)

        # Timeline event
        AccessoryEvent.objects.create(
            accessory=accessory,
            user=user,
            quantity=quantity,
            quantity_change=0,
            event_type=AccessoryEvent.EventType.RETURN_REQUESTED,
            reported_by=user,
            notes=notes,
        )
    ReturnRequestItem.objects.bulk_create(items)

    return request

@transaction.atomic
def create_consumable_return_request(user, consumable_payload, notes=""):

    MAX_ASSETS_PER_REQUEST = 20

    if len(consumable_payload) > MAX_ASSETS_PER_REQUEST:
        raise ValidationError(
            f"Maximum {MAX_ASSETS_PER_REQUEST} consumables can be returned per request."
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
                get_user_consumables(user)
                .select_related("consumable")
                .get(consumable__public_id=consumable_id)
            )
        except ConsumableIssue.DoesNotExist:
            raise ValidationError(
                f"{consumable_id} is not issued to this user."
            )

        # Ensure return quantity is valid
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

        item = ReturnRequestItem(
            return_request=request,
            item_type="consumable",
            consumable_issue=issue,
            quantity=quantity,
            room=consumable.room
        )

        item.public_id = generate_public_id("RRI")
        items.append(item)

        # Timeline event
        ConsumableEvent.objects.create(
            consumable=consumable,
            issue=issue,
            user=user,
            quantity=quantity,
            quantity_change=0,
            event_type=ConsumableEvent.EventType.RETURN_REQUESTED,
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
        .prefetch_related(
            "items",
            "items__equipment_assignment__equipment",
            "items__accessory_assignment__accessory",
            "items__consumable_issue__consumable",
        )
        .get(pk=return_request.pk)
    )

    if rr.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    now = timezone.now()

    for item in rr.items.all():
        if item.status == ReturnRequestItem.Status.PENDING:
            approve_return_item(item, admin_user)

    rr.processed_by = admin_user
    rr.processed_at = now

    update_return_request_status(rr)

    rr.save(update_fields=["status", "processed_by", "processed_at"])

    return rr

@transaction.atomic
def deny_return_request(return_request, admin_user, reason=""):

    rr = (
        ReturnRequest.objects
        .select_for_update()
        .prefetch_related("items")
        .get(pk=return_request.pk)
    )

    if rr.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    now = timezone.now()

    for item in rr.items.all():
        if item.status == ReturnRequestItem.Status.PENDING:
            deny_return_item(item, admin_user, reason)

    rr.processed_by = admin_user
    rr.processed_at = now

    update_return_request_status(rr)

    rr.notes = reason

    rr.save(update_fields=[
        "status",
        "processed_by",
        "processed_at",
        "notes"
    ])

    return rr

def update_return_request_status(rr):

    statuses = set(rr.items.values_list("status", flat=True))

    if statuses == {"approved"}:
        rr.status = ReturnRequest.Status.APPROVED

    elif statuses == {"denied"}:
        rr.status = ReturnRequest.Status.DENIED

    elif "approved" in statuses and "denied" in statuses:
        rr.status = ReturnRequest.Status.PARTIAL

    else:
        rr.status = ReturnRequest.Status.PENDING

    rr.save(update_fields=["status"])

@transaction.atomic
def approve_return_item(item, admin_user):

    if item.status != ReturnRequestItem.Status.PENDING:
        raise ValueError("Item already processed")

    now = timezone.now()

    if item.item_type == "equipment":

        assignment = item.equipment_assignment
        equipment = assignment.equipment

        assignment.returned_at = now
        assignment.save(update_fields=["returned_at"])

        EquipmentEvent.objects.create(
            equipment=equipment,
            user=assignment.user,
            event_type=EquipmentEvent.Event_Choices.RETURNED,
            reported_by=admin_user,
        )

    elif item.item_type == "accessory":

        assignment = item.accessory_assignment
        accessory = assignment.accessory
        qty = item.quantity

        if qty > assignment.quantity:
            raise ValidationError("Return quantity exceeds assignment")

        assignment.quantity -= qty
        assignment.save(update_fields=["quantity"])

        accessory.quantity += qty
        accessory.save(update_fields=["quantity"])

        AccessoryEvent.objects.create(
            accessory=accessory,
            user=assignment.user,
            quantity=qty,
            quantity_change=qty,
            event_type=AccessoryEvent.EventType.RETURNED,
            reported_by=admin_user,
        )

    elif item.item_type == "consumable":

        issue = item.consumable_issue
        consumable = issue.consumable
        qty = item.quantity

        if qty > issue.quantity:
            raise ValidationError("Return quantity exceeds assignment")

        issue.quantity -= qty
        issue.save(update_fields=["quantity"])

        consumable.quantity += qty
        consumable.save(update_fields=["quantity"])

        ConsumableEvent.objects.create(
            consumable=consumable,
            issue=issue,
            user=issue.user,
            quantity=qty,
            quantity_change=qty,
            event_type=ConsumableEvent.EventType.RETURNED,
            reported_by=admin_user,
        )

    item.status = ReturnRequestItem.Status.APPROVED
    item.verified_by = admin_user
    item.verified_at = now

    item.save(update_fields=[
        "status",
        "verified_by",
        "verified_at"
    ])

    update_return_request_status(item.return_request)

@transaction.atomic
def deny_return_item(item, admin_user, reason=""):

    if item.status != ReturnRequestItem.Status.PENDING:
        raise ValueError("Item already processed")

    item.status = ReturnRequestItem.Status.DENIED
    item.verified_by = admin_user
    item.verified_at = timezone.now()
    item.notes = reason

    item.save(update_fields=[
        "status",
        "verified_by",
        "verified_at",
        "notes"
    ])

    update_return_request_status(item.return_request)


@transaction.atomic
def create_mixed_return_request(user, items_payload, notes=""):

    MAX_TOTAL_ITEMS = 20

    if len(items_payload) > MAX_TOTAL_ITEMS:
        raise ValidationError(
            f"Maximum {MAX_TOTAL_ITEMS} items allowed per request."
        )

    request = ReturnRequest.objects.create(
        requester=user,
        notes=notes
    )

    equipment_ids = []
    accessory_payload = []
    consumable_payload = []

    # -----------------------------
    # Split payload by type
    # -----------------------------
    for item in items_payload:

        item_type = item.get("asset_type")

        if item_type == "equipment":
            equipment_ids.append(item["public_id"])

        elif item_type == "accessory":
            accessory_payload.append({
                "accessory_public_id": item["public_id"],
                "quantity": item["quantity"],
            })

        elif item_type == "consumable":
            consumable_payload.append({
                "consumable_public_id": item["public_id"],
                "quantity": item["quantity"],
            })

        else:
            raise ValidationError(f"Invalid asset type: {item_type}")

    # -----------------------------
    # Build items via builders 🔥
    # -----------------------------
    all_items = []

    if equipment_ids:
        all_items.extend(
            build_equipment_return_items(
                user,
                equipment_ids,
                request,
                notes
            )
        )

    if accessory_payload:
        all_items.extend(
            build_accessory_return_items(
                user,
                accessory_payload,
                request,
                notes
            )
        )

    if consumable_payload:
        all_items.extend(
            build_consumable_return_items(
                user,
                consumable_payload,
                request,
                notes
            )
        )

    # -----------------------------
    # Bulk insert
    # -----------------------------
    ReturnRequestItem.objects.bulk_create(all_items)

    return request
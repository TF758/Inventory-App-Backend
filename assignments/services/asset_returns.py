from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from assignments.models.asset_assignment import AccessoryEvent, ConsumableEvent, EquipmentEvent, ReturnRequest, ReturnRequestItem
from assignments.services.asset_return_builders import build_accessory_return_items, build_consumable_return_items, build_equipment_return_items



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
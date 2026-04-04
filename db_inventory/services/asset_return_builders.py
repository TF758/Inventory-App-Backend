from db_inventory.models.asset_assignment import AccessoryEvent, ConsumableEvent, EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem
from db_inventory.models.base import generate_public_id
from db_inventory.utils.query_helpers import get_user_accessories, get_user_consumables
from django.core.exceptions import ValidationError

from db_inventory.utils.ids import generate_unique_prefixed_id

def build_equipment_return_items(user, equipment_public_ids, request, notes):

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

    pending_ids = set(
        ReturnRequestItem.objects.filter(
            equipment_assignment__in=assignments,
            return_request__status=ReturnRequest.Status.PENDING
        ).values_list("equipment_assignment_id", flat=True)
    )

    items = []

    for assignment in assignments:

        if assignment.id in pending_ids:
            raise ValidationError(
                f"{assignment.equipment.public_id} already has a pending return request"
            )

        equipment = assignment.equipment

        item = ReturnRequestItem(
            return_request=request,
            item_type="equipment",
            equipment_assignment=assignment,
            room=equipment.room
        )

        item.public_id = generate_unique_prefixed_id(
                ReturnRequestItem,
                "RRI"
            )
        items.append(item)

        # timeline event
        EquipmentEvent.objects.create(
            equipment=equipment,
            user=user,
            event_type=EquipmentEvent.Event_Choices.RETURN_REQUESTED,
            reported_by=user,
            notes=notes
        )

    return items

def build_accessory_return_items(user, accessory_payload, request, notes):

    MAX_ASSET_PAYLOAD = 20

    if len(accessory_payload) > MAX_ASSET_PAYLOAD:
        raise ValidationError(
            f"Maximum {MAX_ASSET_PAYLOAD} accessories allowed per return request."
        )

    accessory_ids = [entry["accessory_public_id"] for entry in accessory_payload]

    assignments = (
        get_user_accessories(user)
        .select_related("accessory")
        .filter(accessory__public_id__in=accessory_ids)
    )

    assignment_map = {
        a.accessory.public_id: a for a in assignments
    }

    # 🔥 preload pending
    pending_ids = set(
        ReturnRequestItem.objects.filter(
            accessory_assignment__in=assignments,
            return_request__status=ReturnRequest.Status.PENDING
        ).values_list("accessory_assignment_id", flat=True)
    )

    items = []

    for entry in accessory_payload:

        accessory_id = entry["accessory_public_id"]
        quantity = entry["quantity"]

        assignment = assignment_map.get(accessory_id)

        if not assignment:
            raise ValidationError(f"{accessory_id} is not assigned to this user.")

        if quantity > assignment.quantity:
            raise ValidationError(
                f"Cannot return more than assigned quantity for {accessory_id}"
            )

        if assignment.id in pending_ids:
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

        item.public_id = generate_unique_prefixed_id(
            ReturnRequestItem,
            "RRI"
        )
        items.append(item)

        AccessoryEvent.objects.create(
            accessory=accessory,
            user=user,
            quantity=quantity,
            quantity_change=0,
            event_type=AccessoryEvent.EventType.RETURN_REQUESTED,
            reported_by=user,
            notes=notes,
        )

    return items

def build_consumable_return_items(user, consumable_payload, request, notes):

    MAX_ASSETS_PER_REQUEST = 20

    if len(consumable_payload) > MAX_ASSETS_PER_REQUEST:
        raise ValidationError(
            f"Maximum {MAX_ASSETS_PER_REQUEST} consumables allowed per request."
        )

    consumable_ids = [entry["consumable_public_id"] for entry in consumable_payload]

    issues = (
        get_user_consumables(user)
        .select_related("consumable")
        .filter(consumable__public_id__in=consumable_ids)
    )

    issue_map = {
        i.consumable.public_id: i for i in issues
    }

    pending_ids = set(
        ReturnRequestItem.objects.filter(
            consumable_issue__in=issues,
            return_request__status=ReturnRequest.Status.PENDING
        ).values_list("consumable_issue_id", flat=True)
    )

    items = []

    for entry in consumable_payload:

        consumable_id = entry["consumable_public_id"]
        quantity = entry["quantity"]

        issue = issue_map.get(consumable_id)

        if not issue:
            raise ValidationError(
                f"{consumable_id} is not issued to this user."
            )

        if quantity > issue.quantity:
            raise ValidationError(
                f"Cannot return more than remaining quantity for {consumable_id}"
            )

        if issue.id in pending_ids:
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

        item.public_id = generate_unique_prefixed_id(ReturnRequestItem,"RRI")
        items.append(item)

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

    return items
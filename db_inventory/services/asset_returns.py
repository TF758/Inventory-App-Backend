from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from db_inventory.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem

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

    request = ReturnRequest.objects.create(
        requester=user,
        notes=notes
    )

    items = []

    for entry in accessory_payload:

        accessory_id = entry["id"]
        quantity = entry["quantity"]

        assignment = AccessoryAssignment.objects.select_related(
            "accessory"
        ).get(
            accessory__public_id=accessory_id,
            user=user
        )

        if quantity > assignment.quantity:
            raise ValidationError(
                f"Cannot return more than assigned quantity for {accessory_id}"
            )

        items.append(
            ReturnRequestItem(
                return_request=request,
                item_type="accessory",
                accessory_assignment=assignment,
                quantity=quantity
            )
        )

    ReturnRequestItem.objects.bulk_create(items)

    return request


@transaction.atomic
def create_consumable_return_request(user, consumable_payload, notes=""):

    request = ReturnRequest.objects.create(
        requester=user,
        notes=notes
    )

    items = []

    for entry in consumable_payload:

        consumable_id = entry["id"]
        quantity = entry["quantity"]

        issue = ConsumableIssue.objects.select_related(
            "consumable"
        ).get(
            consumable__public_id=consumable_id,
            user=user
        )

        if quantity > issue.quantity:
            raise ValidationError(
                f"Cannot return more than remaining quantity for {consumable_id}"
            )

        items.append(
            ReturnRequestItem(
                return_request=request,
                item_type="consumable",
                consumable_issue=issue,
                quantity=quantity
            )
        )

    ReturnRequestItem.objects.bulk_create(items)

    return request

@transaction.atomic
def approve_return_request(request, admin_user):

    if request.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    for item in request.items.select_related(
        "equipment_assignment",
        "accessory_assignment",
        "consumable_issue"
    ):

        if item.item_type == "equipment":

            assignment = item.equipment_assignment
            equipment = assignment.equipment

            assignment.returned_at = timezone.now()
            assignment.save(update_fields=["returned_at"])

            equipment.status = "AVAILABLE"
            equipment.save(update_fields=["status"])


        elif item.item_type == "accessory":

            assignment = item.accessory_assignment
            accessory = assignment.accessory

            assignment.quantity -= item.quantity
            assignment.save(update_fields=["quantity"])

            accessory.quantity += item.quantity
            accessory.save(update_fields=["quantity"])


        elif item.item_type == "consumable":

            issue = item.consumable_issue
            consumable = issue.consumable

            issue.quantity -= item.quantity
            issue.save(update_fields=["quantity"])

            consumable.quantity += item.quantity
            consumable.save(update_fields=["quantity"])


        item.verified_by = admin_user
        item.verified_at = timezone.now()
        item.save(update_fields=["verified_by", "verified_at"])


    request.status = ReturnRequest.Status.APPROVED
    request.processed_by = admin_user
    request.processed_at = timezone.now()

    request.save(update_fields=[
        "status",
        "processed_by",
        "processed_at"
    ])

def deny_return_request(request, admin_user, reason=""):

    if request.status != ReturnRequest.Status.PENDING:
        raise ValueError("Request already processed")

    request.status = ReturnRequest.Status.DENIED
    request.processed_by = admin_user
    request.processed_at = timezone.now()
    request.notes = reason

    request.save(update_fields=[
        "status",
        "processed_by",
        "processed_at",
        "notes"
    ])
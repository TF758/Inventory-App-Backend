from assignments.models.asset_assignment import EquipmentAssignment, EquipmentEvent, ReturnRequest, ReturnRequestItem
from assets.models.assets import Accessory, Consumable, Equipment, EquipmentStatus
from django.core.exceptions import ValidationError

from core.models.audit import AuditLog
from core.permissions.helpers import can_soft_delete_asset
from core.models.base import generate_public_id


def equipment_event_from_status(status: str) -> str:
    """
    Translate an equipment status change into a domain event.

    Status = current state
    Event  = something that happened

    This mapping MUST be exhaustive.
    """
    STATUS_TO_EVENT = {
        "ok": "repaired",
        "lost": "lost",
        "damaged": "damaged",
        "under_repair": "sent_for_repair",
        "retired": "retired",
         "condemned": "condemned",
    }

    try:
        return STATUS_TO_EVENT[status]
    except KeyError:
        raise ValidationError(
            f"No event mapping defined for equipment status '{status}'"
        )

ASSET_CONFIG = {
    Equipment: {
        "model_name": "Equipment",
        "soft_delete_event": AuditLog.Events.MODEL_DELETED,
        "hard_delete_event": AuditLog.Events.MODEL_PERMANENTLY_DELETED,
        "restore_event": AuditLog.Events.ASSET_RESTORED,
        "permission": can_soft_delete_asset,
    },
    Accessory: {
        "model_name": "Accessory",
        "soft_delete_event": AuditLog.Events.MODEL_DELETED,
        "hard_delete_event": AuditLog.Events.MODEL_PERMANENTLY_DELETED,
        "restore_event": AuditLog.Events.ASSET_RESTORED,
        "permission": can_soft_delete_asset,
    },
    Consumable: {
        "model_name": "Consumable",
        "soft_delete_event": AuditLog.Events.MODEL_DELETED,
        "hard_delete_event": AuditLog.Events.MODEL_PERMANENTLY_DELETED,
        "restore_event": AuditLog.Events.ASSET_RESTORED,
        "permission": can_soft_delete_asset,
    },
}


class SelfAssetBuilder:

    """Utility class to standardize the assets owned by a person"""

    @staticmethod
    def from_equipment(obj):
        return {
            "asset_type": "equipment", 
            "public_id": obj.equipment.public_id,
            "name": obj.equipment.name,
            "room": getattr(obj.equipment.room, "name", None),
            "assigned_at": obj.assigned_at,
            "quantity": 1,
            "available_return_quantity": 1,
            "has_pending_return_request": obj.has_pending_return_request,
            "can_return": not obj.has_pending_return_request,
        }

    @staticmethod
    def from_accessory(obj):
        return {
            "asset_type": "accessory", 
            "public_id": obj.accessory.public_id,
            "name": obj.accessory.name,
            "room": getattr(obj.accessory.room, "name", None),
            "assigned_at": obj.assigned_at,
            "quantity": obj.quantity,
            "available_return_quantity": obj.available_return_quantity,
            "has_pending_return_request": obj.has_pending_return_request,
            "can_return": obj.available_return_quantity > 0,
        }

    @staticmethod
    def from_consumable(obj):
        return {
            "asset_type": "consumable", 
            "public_id": obj.consumable.public_id,
            "name": obj.consumable.name,
            "room": getattr(obj.consumable.room, "name", None),
            "assigned_at": obj.assigned_at,
            "quantity": obj.quantity,
            "available_return_quantity": obj.available_return_quantity,
            "has_pending_return_request": obj.has_pending_return_request,
            "can_return": obj.available_return_quantity > 0,
        }
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

        item.public_id = generate_public_id("RRI")
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
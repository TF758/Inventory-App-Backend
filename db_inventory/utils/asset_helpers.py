from db_inventory.models.asset_assignment import EquipmentEvent
from db_inventory.models.assets import Accessory, Consumable, Equipment, EquipmentStatus
from django.core.exceptions import ValidationError

from db_inventory.models.audit import AuditLog
from db_inventory.permissions.helpers import can_soft_delete_asset


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
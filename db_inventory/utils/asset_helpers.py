from db_inventory.models.asset_assignment import EquipmentEvent
from db_inventory.models.assets import EquipmentStatus
from django.core.exceptions import ValidationError


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
    }

    try:
        return STATUS_TO_EVENT[status]
    except KeyError:
        raise ValidationError(
            f"No event mapping defined for equipment status '{status}'"
        )
from assets.selectors.base import equipment_queryset
from assets.models.assets import EquipmentStatus


def damaged_equipment_queryset():
    return equipment_queryset().filter(
        status=EquipmentStatus.DAMAGED
    )


def equipment_under_repair_queryset():
    return equipment_queryset().filter(
        status=EquipmentStatus.UNDER_REPAIR
    )

def active_equipment_queryset():
    return equipment_queryset().filter(
        status__in=[
            EquipmentStatus.OK,
            EquipmentStatus.UNDER_REPAIR,
            EquipmentStatus.DAMAGED,
        ]
    )


def equipment_ok_queryset():
    return equipment_queryset().filter(
        status=EquipmentStatus.OK
    )


def damaged_equipment_queryset():
    return equipment_queryset().filter(
        status=EquipmentStatus.DAMAGED
    )


def equipment_under_repair_queryset():
    return equipment_queryset().filter(
        status=EquipmentStatus.UNDER_REPAIR
    )


def department_equipment_queryset(department):
    """
    Active equipment assigned to a department.
    """
    return equipment_queryset().filter(
        room__location__department=department
    )

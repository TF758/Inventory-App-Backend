from assets.models import  Equipment, Accessory, Consumable, Component


# ==========================================================
# Equipment
# ==========================================================

def equipment_queryset():
    """
    Active/Not deleted equipment only.
    """
    return Equipment.objects.filter(
        is_deleted=False
    )


def deleted_equipment_queryset():
    """
    Soft-deleted equipment only.
    """
    return Equipment.objects.filter(
        is_deleted=True
    )


def all_equipment_queryset():
    """
    Includes active and deleted equipment.
    """
    return Equipment.objects.all()


# ==========================================================
# Accessories
# ==========================================================

def accessory_queryset():
    """
    Active accessories only.
    """
    return Accessory.objects.filter(
        is_deleted=False
    )


def deleted_accessory_queryset():
    """
    Soft-deleted accessories only.
    """
    return Accessory.objects.filter(
        is_deleted=True
    )


def all_accessory_queryset():
    """
    Includes active and deleted accessories.
    """
    return Accessory.objects.all()


# ==========================================================
# Consumables
# ==========================================================

def consumable_queryset():
    """
    Active consumables only.
    """
    return Consumable.objects.filter(
        is_deleted=False
    )


def deleted_consumable_queryset():
    """
    Soft-deleted consumables only.
    """
    return Consumable.objects.filter(
        is_deleted=True
    )


def all_consumable_queryset():
    """
    Includes active and deleted consumables.
    """
    return Consumable.objects.all()

# ==========================================================
# Users
# ==========================================================

# ==========================================================
# Components
# ==========================================================

def component_queryset():
    """
    Active components only.
    """
    return Component.objects.filter(
        is_deleted=False
    )


def deleted_component_queryset():
    """
    Soft-deleted components only.
    """
    return Component.objects.filter(
        is_deleted=True
    )


def all_component_queryset():
    """
    Includes active and deleted components.
    """
    return Component.objects.all()


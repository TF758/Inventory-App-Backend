from django.db.models import Sum, F

def calculate_inventory_values(
    equipment_qs,
    accessory_qs,
    consumable_qs,
):
    """
    Calculate inventory valuation for a given scope.

    Returns:
    {
        "equipment_value": Decimal,
        "accessory_value": Decimal,
        "consumable_value": Decimal,
        "total_inventory_value": Decimal,
    }
    """

    equipment_value = (
        equipment_qs.aggregate(
            total=Sum("purchase_price")
        )["total"]
        or 0
    )

    accessory_value = (
        accessory_qs.aggregate(
            total=Sum(
                F("quantity") * F("unit_cost")
            )
        )["total"]
        or 0
    )

    consumable_value = (
        consumable_qs.aggregate(
            total=Sum(
                F("quantity") * F("unit_cost")
            )
        )["total"]
        or 0
    )

    total_inventory_value = (
        equipment_value
        + accessory_value
        + consumable_value
    )

    return {
        "equipment_value": equipment_value,
        "accessory_value": accessory_value,
        "consumable_value": consumable_value,
        "total_inventory_value": total_inventory_value,
    }
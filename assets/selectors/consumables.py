from django.db.models import F
from assets.selectors.base import consumable_queryset


def low_stock_consumables_queryset():
    return consumable_queryset().filter(
        low_stock_threshold__gt=0,
        quantity__lte=F("low_stock_threshold"),
    )


def department_consumables_queryset(department):
    """
    Active consumables assigned to a department.
    """
    return consumable_queryset().filter(
        room__location__department=department
    )

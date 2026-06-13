from assets.selectors.base import accessory_queryset


def department_accessories_queryset(
    department
):
    return accessory_queryset().filter(
        room__location__department=department
    )


def department_accessories_queryset(department):
    """
    Active accessories assigned to a department.
    """
    return accessory_queryset().filter(
        room__location__department=department
    )

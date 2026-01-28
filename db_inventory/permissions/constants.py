
# Role hierarchy: higher numbers mean more power
from db_inventory.models.assets import EquipmentStatus


ROLE_HIERARCHY = {
    # Room roles
    "ROOM_VIEWER": 0,
    "ROOM_CLERK": 1,
    "ROOM_ADMIN": 2,

    # Location roles
    "LOCATION_VIEWER": 3,
    "LOCATION_ADMIN": 4,

    # Department roles
    "DEPARTMENT_VIEWER": 5,
    "DEPARTMENT_ADMIN": 6,

    # Site-wide admin
    "SITE_ADMIN": 99,
}

OWNER_ALLOWED_STATUSES = {
    EquipmentStatus.OK,
    EquipmentStatus.DAMAGED,
    EquipmentStatus.UNDER_REPAIR,
}

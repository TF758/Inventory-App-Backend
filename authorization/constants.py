SYSTEM_ROLES = {
    "ROOM_VIEWER": {
        "scope_type": "ROOM",
        "level": 10,
    },
    "ROOM_CLERK": {
        "scope_type": "ROOM",
        "level": 20,
    },
    "ROOM_ADMIN": {
        "scope_type": "ROOM",
        "level": 30,
    },
    "LOCATION_VIEWER": {
        "scope_type": "LOCATION",
        "level": 40,
    },
    "LOCATION_ADMIN": {
        "scope_type": "LOCATION",
        "level": 50,
    },
    "DEPARTMENT_VIEWER": {
        "scope_type": "DEPARTMENT",
        "level": 60,
    },
    "DEPARTMENT_ADMIN": {
        "scope_type": "DEPARTMENT",
        "level": 70,
    },
    "SITE_ADMIN": {
        "scope_type": "GLOBAL",
        "level": 100,
    },
}


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

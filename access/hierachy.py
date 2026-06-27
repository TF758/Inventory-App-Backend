"""
Site hierarchy configuration.

Defines where each role may be assigned,
which levels of the site hierarchy it may navigate,
and which roles it may govern.

This configuration is intentionally separate
from permissions.

Permissions determine WHAT a role can do.

Hierarchy determines WHERE within the site
structure that role may operate.

Governance determines WHICH roles this role
may assign, update, or delete.
"""

SITE = "site"
DEPARTMENT = "department"
LOCATION = "location"
ROOM = "room"

MANAGES_ALL = "__all__"


ROLE_HIERARCHY_LIST = {

    # --------------------------------------------------
    # Site
    # --------------------------------------------------

    "SITE_ADMIN": {
        "assign": {
            SITE,
        },
        "access": {
            DEPARTMENT,
            LOCATION,
            ROOM,
        },
        "manages": MANAGES_ALL,
    },

    # --------------------------------------------------
    # Department
    # --------------------------------------------------

    "DEPARTMENT_ADMIN": {
        "assign": {
            DEPARTMENT,
        },
        "access": {
            DEPARTMENT,
            LOCATION,
            ROOM,
        },
        "manages": {
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
    },

    "DEPARTMENT_VIEWER": {
        "assign": {
            DEPARTMENT,
        },
        "access": {
            DEPARTMENT,
            LOCATION,
            ROOM,
        },
        "manages": set(),
    },

    # --------------------------------------------------
    # Location
    # --------------------------------------------------

    "LOCATION_ADMIN": {
        "assign": {
            LOCATION,
        },
        "access": {
            LOCATION,
            ROOM,
        },
        "manages": {
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
    },

    "LOCATION_VIEWER": {
        "assign": {
            LOCATION,
        },
        "access": {
            LOCATION,
            ROOM,
        },
        "manages": set(),
    },

    # --------------------------------------------------
    # Room
    # --------------------------------------------------

    "ROOM_ADMIN": {
        "assign": {
            ROOM,
        },
        "access": {
            ROOM,
        },
        "manages": {
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
    },

    "ROOM_CLERK": {
        "assign": {
            ROOM,
        },
        "access": {
            ROOM,
        },
        "manages": set(),
    },

    "ROOM_VIEWER": {
        "assign": {
            ROOM,
        },
        "access": {
            ROOM,
        },
        "manages": set(),
    },
}
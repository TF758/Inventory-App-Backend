"""
Site hierarchy configuration.

Defines where each role may be assigned and
which levels of the site hierarchy it may
navigate.

This configuration is intentionally separate
from permissions.

Permissions determine WHAT a role can do.

Hierarchy determines WHERE within the site
structure that role may operate.
"""

SITE = "site"
DEPARTMENT = "department"
LOCATION = "location"
ROOM = "room"


ROLE_HIERARCHY = {

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
    },

    "LOCATION_VIEWER": {
        "assign": {
            LOCATION,
        },
        "access": {
            LOCATION,
            ROOM,
        },
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
    },

    "ROOM_CLERK": {
        "assign": {
            ROOM,
        },
        "access": {
            ROOM,
        },
    },

    "ROOM_VIEWER": {
        "assign": {
            ROOM,
        },
        "access": {
            ROOM,
        },
    },
}
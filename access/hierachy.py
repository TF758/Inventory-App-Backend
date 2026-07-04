"""
Site hierarchy and role governance configuration.

This module defines three related but separate concepts:

1. assign
   The hierarchy level where this role type itself may be assigned.

   Example:
   LOCATION_ADMIN has assign={LOCATION}, meaning a LOCATION_ADMIN role
   is attached to a specific location.

2. access
   The hierarchy levels this role may navigate or operate within,
   subject to object scope checks.

   Example:
   DEPARTMENT_ADMIN has access={DEPARTMENT, LOCATION, ROOM},
   meaning it may access its department, locations under that department,
   and rooms under those locations.

3. manages
   The role types this role may assign, update, or remove for other users.

   Example:
   LOCATION_ADMIN can manage LOCATION_VIEWER and room-level roles inside
   its permitted location scope.

This configuration is intentionally separate from permissions.

Permissions determine WHAT a role can do.

Hierarchy determines WHERE within the site structure that role may operate.

Governance determines WHICH role types this role may assign, update, or delete.

Scope checks still apply. A role may only manage another role assignment
when the target role is both allowed by this governance configuration and
inside the active role's permitted scope.
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
        # Site Admin is assigned at the site level.
        "assign": {
            SITE,
        },

        # Site Admin can navigate the full hierarchy.
        "access": {
            DEPARTMENT,
            LOCATION,
            ROOM,
        },

        # Site Admin can govern all role types.
        "manages": MANAGES_ALL,
    },

    # --------------------------------------------------
    # Department
    # --------------------------------------------------

    "DEPARTMENT_ADMIN": {
        # Department Admin is assigned to one department.
        "assign": {
            DEPARTMENT,
        },

        # Department Admin can access its department,
        # locations inside it, and rooms inside those locations.
        "access": {
            DEPARTMENT,
            LOCATION,
            ROOM,
        },

        # Department Admin can manage viewer access at its own level
        # and administrative/viewer roles below it.
        "manages": {
            "DEPARTMENT_VIEWER",
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
    },

    "DEPARTMENT_VIEWER": {
        # Department Viewer is assigned to one department.
        "assign": {
            DEPARTMENT,
        },

        # Department Viewer can read/navigate its department hierarchy
        # only when paired with the relevant view permissions.
        "access": {
            DEPARTMENT,
            LOCATION,
            ROOM,
        },

        # Viewers do not govern other roles.
        "manages": set(),
    },

    # --------------------------------------------------
    # Location
    # --------------------------------------------------

    "LOCATION_ADMIN": {
        # Location Admin is assigned to one location.
        "assign": {
            LOCATION,
        },

        # Location Admin can access its location and rooms under it.
        "access": {
            LOCATION,
            ROOM,
        },

        # Location Admin can manage viewer access at its own level
        # and room-level roles below it.
        "manages": {
            "LOCATION_VIEWER",
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
    },

    "LOCATION_VIEWER": {
        # Location Viewer is assigned to one location.
        "assign": {
            LOCATION,
        },

        # Location Viewer can read/navigate its location hierarchy
        # only when paired with the relevant view permissions.
        "access": {
            LOCATION,
            ROOM,
        },

        # Viewers do not govern other roles.
        "manages": set(),
    },

    # --------------------------------------------------
    # Room
    # --------------------------------------------------

    "ROOM_ADMIN": {
        # Room Admin is assigned to one room.
        "assign": {
            ROOM,
        },

        # Room Admin can access only its assigned room.
        "access": {
            ROOM,
        },

        # Room Admin can manage operational/viewer access inside its room.
        "manages": {
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
    },

    "ROOM_CLERK": {
        # Room Clerk is assigned to one room.
        "assign": {
            ROOM,
        },

        # Room Clerk can access only its assigned room.
        "access": {
            ROOM,
        },

        # Clerks do not govern other roles.
        "manages": set(),
    },

    "ROOM_VIEWER": {
        # Room Viewer is assigned to one room.
        "assign": {
            ROOM,
        },

        # Room Viewer can access only its assigned room.
        "access": {
            ROOM,
        },

        # Viewers do not govern other roles.
        "manages": set(),
    },
}
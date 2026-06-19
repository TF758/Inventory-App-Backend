from rest_framework.exceptions import PermissionDenied

from authorization.helpers import is_in_scope
from authorization.services import (
    get_active_role,
    user_has_permission,
)


def can_create_room( *, actor, location, ) -> bool:
    """
    Business-rule validation for room creation.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    if not user_has_permission(
        actor,
        "rooms.create",
    ):
        return False

    return is_in_scope(
        role,
        location=location,
    )


def ensure_can_create_room(**kwargs):
    if not can_create_room(**kwargs):
        raise PermissionDenied(
            "You cannot create rooms in this location."
        )

def can_transfer_room( *, actor, room, new_location, ) -> bool:
    """
    Business-rule validation for moving a room
    to another location.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    if not user_has_permission(
        actor,
        "rooms.transfer",
    ):
        return False

    # Must have authority over source room
    if not is_in_scope(
        role,
        room=room,
    ):
        return False

    # Must have authority over destination location
    if not is_in_scope(
        role,
        location=new_location,
    ):
        return False

    return True


def ensure_can_transfer_room(**kwargs):
    if not can_transfer_room(**kwargs):
        raise PermissionDenied(
            "You cannot transfer this room."
        )

def can_create_location( *, actor, department, ) -> bool:
    """
    Business-rule validation for location creation.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    if not user_has_permission( actor, "locations.create", ):
        return False

    return is_in_scope(
        role,
        department=department,
    )


def ensure_can_create_location(**kwargs):
    if not can_create_location(**kwargs):
        raise PermissionDenied(
            "You cannot create locations in this department."
        )

def can_transfer_location( *, actor, location, new_department, ) -> bool:
    """
    Business-rule validation for moving a location
    between departments.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    if not user_has_permission( actor, "locations.transfer", ):
        return False

    # Must control source location
    if not is_in_scope( role, location=location, ):
        return False

    # Must control destination department
    if not is_in_scope(
        role,
        department=new_department,
    ):
        return False

    return True


def ensure_can_transfer_location(**kwargs):
    if not can_transfer_location(**kwargs):
        raise PermissionDenied(
            "You cannot transfer this location."
        )
    

def can_create_department( *, actor, ) -> bool:
    """
    Business-rule validation for department creation.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    return user_has_permission(
        actor,
        "departments.create",
    )


def ensure_can_create_department(**kwargs):
    if not can_create_department(**kwargs):
        raise PermissionDenied(
            "You cannot create departments."
        )

def can_update_department( *, actor, department, ) -> bool:
    """
    Business-rule validation for department updates.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    return user_has_permission(
        actor,
        "departments.update",
    )


def ensure_can_update_department(**kwargs):
    if not can_update_department(**kwargs):
        raise PermissionDenied(
            "You cannot update this department."
        )

def can_delete_department( *, actor, department, ) -> bool:
    """
    Business-rule validation for department deletion.
    """

    role = get_active_role(actor)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    return user_has_permission(
        actor,
        "departments.delete",
    )


def ensure_can_delete_department(**kwargs):
    if not can_delete_department(**kwargs):
        raise PermissionDenied(
            "You cannot delete this department."
        )
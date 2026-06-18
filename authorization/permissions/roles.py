from rest_framework.exceptions import PermissionDenied
from authorization.helpers import is_in_scope
from authorization.permissions.base_permissions import ScopedPermission
from authorization.services import get_active_role
from core.permissions.helpers import ensure_permission


class RoleAssignmentPermission( ScopedPermission ):

    permission_map = {
        "GET": "role_assignments.view",
        "POST": "role_assignments.create",
        "PUT": "role_assignments.update",
        "PATCH": "role_assignments.update",
        "DELETE": "role_assignments.delete",
    }


def can_assign_role( *, actor, target_role, room=None, location=None, department=None, ) -> bool:
    """
    Business validation for role assignment.

    Assumes endpoint capability checks have
    already been performed by RoleAssignmentPermission.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True

    return is_in_scope(
        active_role,
        room=room,
        location=location,
        department=department,
    )

def can_update_role_assignment( *, actor, assignment, new_role=None, room=None, location=None, department=None, ) -> bool:
    """
    Business validation for role assignment updates.

    Assumes endpoint capability checks have
    already been performed by RoleAssignmentPermission.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True

    target_room = room or assignment.room
    target_location = location or assignment.location
    target_department = department or assignment.department

    return is_in_scope(
        active_role,
        room=target_room,
        location=target_location,
        department=target_department,
    )


def can_delete_role_assignment( *, actor, assignment, ) -> bool:
    """
    Business validation for role assignment deletion.

    Assumes endpoint capability checks have
    already been performed by RoleAssignmentPermission.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True

    return is_in_scope(
        active_role,
        room=assignment.room,
        location=assignment.location,
        department=assignment.department,
    )


def ensure_can_assign_role(**kwargs):
    if not can_assign_role(**kwargs):
        raise PermissionDenied(
            "You cannot assign roles in this scope."
        )


def ensure_can_update_role_assignment(**kwargs):
    if not can_update_role_assignment(**kwargs):
        raise PermissionDenied(
            "You cannot modify role assignments in this scope."
        )


def ensure_can_delete_role_assignment(**kwargs):
    if not can_delete_role_assignment(**kwargs):
        raise PermissionDenied(
            "You cannot delete role assignments in this scope."
        )
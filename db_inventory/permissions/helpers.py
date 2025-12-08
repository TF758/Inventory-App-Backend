# myapp/permissions/helpers.py
from typing import Optional
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from db_inventory.models import *
from .constants import ROLE_HIERARCHY


def can_modify(user_role: str, target_role: str) -> bool:
    """
    Returns True if the given role is allowed to perform the action implied by target_role.
    
    Rules:
    - VIEWER roles can be assigned by users of equal or higher hierarchy.
    - All other roles require the user to be strictly higher in hierarchy.
    - SITE_ADMIN can assign anything.
    """
    if user_role.endswith("_VIEWER") and not target_role.endswith("_VIEWER"):
        return False
    
    if user_role == "SITE_ADMIN":
        return True

    if target_role.endswith("_VIEWER"):
        return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(target_role, -1)
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(target_role, -1)

def get_active_role(user: User) -> Optional[RoleAssignment]:
    """
    Retrieve the active role assignment for a user.
    """
    return getattr(user, "active_role", None)

def get_user_roles(user: User):
    """
    Get all role assignments for a given user.
    """
    return RoleAssignment.objects.filter(user=user)

def has_hierarchy_permission(user_role: str, required_role: str) -> bool:
    """
    Check whether a user's role level is equal to or higher than the required role
    according to the defined role hierarchy.

    Returns:
        bool: True if user_role >= required_role in hierarchy, otherwise False.
    """
    if user_role == "SITE_ADMIN":
        return True
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, -1)

def is_in_scope(role_assignment: RoleAssignment,
                room: Optional[Room] = None,
                location: Optional[Location] = None,
                department: Optional[Department] = None) -> bool:
    """
    Determine whether a role assignment has scope over a given resource
    (room, location, or department).

    Returns:
        bool: True if the role covers the given resource, otherwise False.
    """

    if not role_assignment:
        return False
    if role_assignment.role == "SITE_ADMIN":
        return True

    if department:
        if role_assignment.department == department:
            return True
        if role_assignment.location and role_assignment.location.department == department:
            return True
        if role_assignment.room and role_assignment.room.location.department == department:
            return True

    if location:
        if role_assignment.location == location:
            return True
        if role_assignment.department and location.department == role_assignment.department:
            return True
        if role_assignment.room and role_assignment.room.location == location:
            return True

    if room:
        if role_assignment.room == room:
            return True
        if role_assignment.location and role_assignment.location == room.location:
            return True
        if role_assignment.department and room.location.department == role_assignment.department:
            return True

    return False

def is_user_in_scope(
                    user: User,
                    room: Optional[Room] = None,
                    location: Optional[Location] = None,
                    department: Optional[Department] = None) -> bool:
    """
    Check if the user's active role has scope over a user.
    Infers the target's scope by checking it's User Locations and Role Assignments.
    Todo: Implement this function.
    """
    pass

def check_permission(user: User, required_role: str,
                     room: Optional[Room] = None,
                     location: Optional[Location] = None,
                     department: Optional[Department] = None) -> bool:
    """
    Verify that the user's active role satisfies both hierarchy and scope
    requirements for a given resource.

    Returns:
        bool: True if the user has permission, otherwise False.
    """
    
    role = getattr(user, "active_role", None)
    if not role:
        return False
    
    if role.role == "SITE_ADMIN":
        return True
    
    # hierarchy check
    if not has_hierarchy_permission(role.role, required_role):
        return False

    # scope check
    if not is_in_scope(role, room, location, department):
        return False

    # prevent view-only roles from performing modify actions
    if not required_role.endswith("_VIEWER") and not can_modify(role.role, required_role):
        return False

    return True

def ensure_permission(user: User, required_role: str,
                      room: Optional[Room] = None,
                      location: Optional[Location] = None,
                      department: Optional[Department] = None):
    """
    Raise a PermissionDenied exception if the user lacks the required role
    or scope for the target resource.

    Raises:
        PermissionDenied: If the user lacks permission for the resource.
    """
    if not check_permission(user, required_role, room, location, department):
        raise PermissionDenied(f"Active role lacks {required_role} permission for this resource.")

def filter_queryset_by_scope(user: User, queryset, model_class):
    """
    Restrict a queryset to the subset of records the user's active role
    has scope over (based on department, location, or room).

    Returns:
        QuerySet: The filtered queryset containing only records within scope.
    """
    active_role = get_active_role(user)
    if not active_role:
        return queryset.none()

    if active_role.role == "SITE_ADMIN":
        return queryset

    q = Q()

    if model_class == Room:
        if active_role.room:
            q |= Q(pk=active_role.room.pk)
        elif active_role.location:
            q |= Q(location=active_role.location)
        elif active_role.department:
            q |= Q(location__department=active_role.department)

    elif model_class == Location:
        if active_role.room:
            return queryset.none()
        if active_role.location:
            q |= Q(pk=active_role.location.pk)
        elif active_role.department:
            q |= Q(department=active_role.department)

    elif model_class == Department:
        if active_role.room or active_role.location:
            return queryset.none()
        if active_role.department:
            q |= Q(pk=active_role.department.pk)

    elif model_class == AuditLog:
        if active_role.room:
            q |= Q(room=active_role.room)
        elif active_role.location:
            q |= Q(location=active_role.location)
        elif active_role.department:
            q |= Q(department=active_role.department)

    elif model_class in (Equipment, Accessory, Consumable):
        if active_role.room:
            q |= Q(room=active_role.room)
        elif active_role.location:
            q |= Q(room__location=active_role.location)
        elif active_role.department:
            q |= Q(room__location__department=active_role.department)

    elif model_class == Component:
        if active_role.room:
            q |= Q(equipment__room=active_role.room)
        elif active_role.location:
            q |= Q(equipment__room__location=active_role.location)
        elif active_role.department:
            q |= Q(equipment__room__location__department=active_role.department)

    elif model_class == RoleAssignment:
        if active_role.room:
            q |= Q(room=active_role.room)
        elif active_role.location:
            q |= Q(location=active_role.location) | Q(room__location=active_role.location)
        elif active_role.department:
            q |= (
                Q(department=active_role.department)
                | Q(location__department=active_role.department)
                | Q(room__location__department=active_role.department)
            )

    elif model_class == UserLocation:
        if active_role.department:
            q |= Q(room__location__department=active_role.department)
        elif active_role.location:
            q |= Q(room__location=active_role.location)
        elif active_role.room:
            q |= Q(room=active_role.room)

    elif model_class.__name__ == "User":
        user_q = Q()
        if active_role.department:
            user_q |= Q(role_assignments__department=active_role.department)
            user_q |= Q(user_locations__room__location__department=active_role.department)
        elif active_role.location:
            user_q |= Q(role_assignments__location=active_role.location)
            user_q |= Q(user_locations__room__location=active_role.location)
        elif active_role.room:
            user_q |= Q(role_assignments__room=active_role.room)
            user_q |= Q(user_locations__room=active_role.room)

        if active_role.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN"]:
            user_q |= Q(active_role__isnull=True,
                        created_by__role_assignments__department=active_role.department)

        if active_role.role == "SITE_ADMIN":
            user_q |= Q()

        q |= user_q

    return queryset.filter(q).distinct()

def is_viewer_role(role: str) -> bool:
    """
    Determines if a given role is a Viewer role.

    Viewer roles are intended to have read-only access,
    meaning they should not perform any write, update, or delete operations.

    Args:
        role (str): The role string to check, e.g., "ROOM_VIEWER", "DEPARTMENT_ADMIN"

    Returns:
        bool: True if the role is a viewer role, False otherwise.
    """
    if not role:
        # No role provided, cannot be a viewer
        return False

    # Normalize to uppercase to be case-insensitive
    role = role.upper()

    # Viewer roles follow the naming convention *_VIEWER
    return role.endswith("_VIEWER")


def is_admin_role(role: str) -> bool:
    """
    Determines if a given role has administrative/write access.

    Admin roles are allowed to perform write, update, or delete operations.
    This excludes viewer roles which are read-only.

    Args:
        role (str): The role string to check, e.g., "ROOM_ADMIN", "DEPARTMENT_VIEWER"

    Returns:
        bool: True if the role has write/admin access, False if it's read-only (viewer) or invalid.
    """
    if not role:
        return False

    role = role.upper()

    # Viewer roles are always read-only
    if role.endswith("_VIEWER"):
        return False

    # Ensure the role exists in ROLE_HIERARCHY
    if role not in ROLE_HIERARCHY:
        return False

    # Any non-viewer role in the hierarchy is considered an admin/write role
    return True
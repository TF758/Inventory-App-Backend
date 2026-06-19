from typing import Optional
from authorization.models import RolePermission
from users.models.users import User
from functools import lru_cache
from core.utils.scope.policies import POLICY_REGISTRY
from sites.models.sites import Department, Location, Room, UserPlacement
from users.models.roles import RoleAssignment


def get_active_role(user):
    """
    Returns the user's active RoleAssignment.

    Existing architecture remains unchanged.
    """
    return getattr(user, "active_role", None)

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
    admin_role: RoleAssignment,
    target_user: User
) -> bool:
    """
    Check whether the admin_role has scope over the target user.
    """

    if not admin_role:
        return False

    if admin_role.role == "SITE_ADMIN":
        return True


    for ra in RoleAssignment.objects.filter(user=target_user):
        if is_in_scope(
            admin_role,
            room=ra.room,
            location=ra.location,
            department=ra.department,
        ):
            return True

    current_ul = (
        UserPlacement.objects
        .select_related("room__location__department")
        .filter(user=target_user, is_current=True)
    )

    for ul in current_ul:
        if not ul.room:
            continue  

        if is_in_scope(
            admin_role,
            room=ul.room,
            location=ul.room.location,
            department=ul.room.location.department,
        ):
            return True

    return False


def filter_queryset_by_scope(user, queryset, model_class):
    """
    Restrict a queryset to the subset of records the user's active role
    has scope over (based on department, location, or room).

    This function delegates filtering to model-specific scope policies.

    Behavior:
        - No active role → empty queryset
        - SITE_ADMIN → full access
        - Otherwise → use registered policy
        - No policy → deny (empty queryset)

    Returns:
        QuerySet filtered according to scope rules
    """
    role = get_active_role(user)

    if not role:
        return queryset.none()

    if role.role == "SITE_ADMIN":
        return queryset

    policy_cls = POLICY_REGISTRY.get(model_class)

    if not policy_cls:
        return queryset.none()

    policy = policy_cls(user, queryset)
    return policy.apply()

def filter_user_assets_by_scope(viewer, queryset, asset_path="room"):
    role = getattr(viewer, "active_role", None)

    if not role:
        return queryset.none()

    if role.role == "SITE_ADMIN":
        return queryset

    if role.room:
        return queryset.filter(**{asset_path: role.room})

    if role.location:
        return queryset.filter(**{f"{asset_path}__location": role.location})

    if role.department:
        return queryset.filter(**{f"{asset_path}__location__department": role.department})

    return queryset.none()




@lru_cache(maxsize=256)
def get_role_permissions(role_public_id):
    """
    Returns a set of permission codes for a role.

    Example:
        {
            "assets.view",
            "assets.create",
            "users.view",
        }
    """

    return set(
        RolePermission.objects.filter(
            role__public_id=role_public_id,
            enabled=True,
        ).values_list(
            "permission__code",
            flat=True,
        )
    )


def role_has_permission( role, permission_code, ):
    """
    Check whether a role has a permission.
    """

    if not role:
        return False

    permissions = get_role_permissions(
        role.public_id,
    )

    return permission_code in permissions



def invalidate_role_permission_cache():
    """
    Utility for admin updates/imports.
    """

    get_role_permissions.cache_clear()
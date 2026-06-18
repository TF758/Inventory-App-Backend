from typing import Optional
from users.models.users import User
from authorization.services import get_active_role, user_has_permission
from core.utils.scope.policies import POLICY_REGISTRY
from sites.models.sites import Department, Location, Room, UserPlacement
from users.models.roles import RoleAssignment


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


def has_asset_custody_scope( role: RoleAssignment, asset ) -> bool:
    """
    Scope check for physical asset custody.
    Prevents upward / sideways authority leakage.
    """

    if role.role == "SITE_ADMIN":
        return True

    if not asset.room:
        return False

    role_name = role.role

    # ROOM roles → exact room only
    if role_name.startswith("ROOM_"):
        return role.room == asset.room

    # LOCATION roles → same location
    if role_name.startswith("LOCATION_"):
        return (
            role.location
            and asset.room.location == role.location
        )

    # DEPARTMENT roles → same department
    if role_name.startswith("DEPARTMENT_"):
        return (
            role.department
            and asset.room.location.department == role.department
        )

    return False

def can_assign_asset_to_user( admin_role: RoleAssignment, target_user: User ) -> bool:
    """
    Determines whether an admin may assign equipment
    to a target user.
    """

    if admin_role.role == "SITE_ADMIN":
        return True

    # ROOM roles → user must be in same room
    if admin_role.role.startswith("ROOM_"):
        return UserPlacement.objects.filter(
            user=target_user,
            room=admin_role.room,
            is_current=True,
        ).exists()

    # LOCATION roles → user must be in same location
    if admin_role.role.startswith("LOCATION_"):
        return UserPlacement.objects.filter(
            user=target_user,
            room__location=admin_role.location,
            is_current=True,
        ).exists()

    # DEPARTMENT roles → user must be in same department
    if admin_role.role.startswith("DEPARTMENT_"):
        return UserPlacement.objects.filter(
            user=target_user,
            room__location__department=admin_role.department,
            is_current=True,
        ).exists()

    return False

def can_soft_delete_asset(
    user,
    asset,
) -> bool:
    """
    Business-rule authorization for soft deletion.

    Requires:
        assets.delete capability
        +
        custody scope
    """

    role = get_active_role(user)

    if not role:
        return False

    if role.role == "SITE_ADMIN":
        return True

    if not user_has_permission(
        user,
        "assets.delete",
    ):
        return False

    return has_asset_custody_scope(
        role,
        asset,
    )



def can_hard_delete_asset(
    user,
    asset=None,
) -> bool:
    """
    Business-rule authorization for
    permanent asset deletion.
    """

    return user_has_permission(
        user,
        "assets.hard_delete",
    )
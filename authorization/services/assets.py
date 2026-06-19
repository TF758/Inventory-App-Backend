


from authorization.helpers import get_active_role
from authorization.services.users import user_has_permission
from sites.models.sites import UserPlacement
from users.models.roles import RoleAssignment
from users.models.users import User




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
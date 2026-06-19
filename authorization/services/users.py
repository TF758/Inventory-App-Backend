
from authorization.helpers import get_active_role, role_has_permission
from functools import lru_cache


def user_has_permission( user, permission_code, ):
    """
    Permission check based on the user's active role.

    Site Admin bypass remains intact.
    """

    active_role = get_active_role(user)

    if not active_role:
        return False

    #
    # Legacy Site Admin bypass
    #
    if active_role.role == "SITE_ADMIN":
        return True

    #
    # During migration RoleAssignment may not yet
    # be backfilled.
    #
    if not active_role.role_ref:
        return False

    return role_has_permission(
        active_role.role_ref,
        permission_code,
    )

from functools import lru_cache

from authorization.models import (
    Permission,
    Role,
    RolePermission,
)


def get_active_role(user):
    """
    Returns the user's active RoleAssignment.

    Existing architecture remains unchanged.
    """
    return getattr(user, "active_role", None)


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


def role_has_permission(
    role,
    permission_code,
):
    """
    Check whether a role has a permission.
    """

    if not role:
        return False

    permissions = get_role_permissions(
        role.public_id,
    )

    return permission_code in permissions


def user_has_permission(
    user,
    permission_code,
):
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


def invalidate_role_permission_cache():
    """
    Utility for admin updates/imports.
    """

    get_role_permissions.cache_clear()
from rest_framework.permissions import BasePermission

class IsActiveSiteAdmin(BasePermission):
    """
    Allows access only when the authenticated user has
    SITE_ADMIN as their currently active role.

    This is intentionally not configurable through
    RolePermission because it protects the permission
    management system itself.
    """

    message = (
        "Only an active Site Admin can manage permissions."
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        active_role = getattr(
            user,
            "active_role",
            None,
        )

        return bool(
            active_role
            and active_role.role == "SITE_ADMIN"
        )
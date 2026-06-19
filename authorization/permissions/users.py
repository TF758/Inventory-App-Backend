
from rest_framework.permissions import BasePermission, SAFE_METHODS
from authorization.permissions.base_permissions import RequiresPermission, ScopedPermission
from authorization.helpers import get_active_role, is_user_in_scope


class UserPlacementPermission(ScopedPermission):
    permission_map = {
        "GET": "user_placements.view",
        "POST": "user_placements.create",
        "PUT": "user_placements.update",
        "PATCH": "user_placements.update",
        "DELETE": "user_placements.delete",
    }

    def get_scope_object(self, obj):
        return getattr(obj, "room", None)

class FullUserCreatePermission(RequiresPermission):
    required_permission = "users.full_create"


class AdminUpdateUserPermission( ScopedPermission ):

    permission_map = {
        "PUT": "users.update",
        "PATCH": "users.update",
    }
    def has_object_permission( self, request, view, obj, ):
            role = get_active_role( request.user )

            if not role:
                return False

            if role.role == "SITE_ADMIN":
                return True

            return is_user_in_scope(
                role,
                obj,
            )

class UserPermission(BasePermission):
    """
    Permissions for user self-service and read-only access.

    Rules:
    - All authenticated users may view users
    - Users may edit themselves
    - No admin-level writes allowed here
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # READ — all authenticated users
        if request.method in SAFE_METHODS:
            return True

        # WRITE — self only
        if request.method in ["PUT", "PATCH"]:
            return user == obj

        return False
    

class UserProfilePermission( RequiresPermission ):
    required_permission = "users.view"

    def has_object_permission( self, request, view, obj, ):
        requester = request.user

        if requester == obj:
            return True

        role = get_active_role(
            requester
        )

        if not role:
            return False

        if role.role == "SITE_ADMIN":
            return True

        return is_user_in_scope( role, obj, )
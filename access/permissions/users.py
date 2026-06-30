# myapp/permissions/users.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from access.permissions.scoped import ScopedPermission
from access.services.scope import ScopeService, UserScopeService
from access.permissions.base import RequiresPermission
from access.services.access import AccessService
from users.models.roles import RoleAssignment

from sites.models.sites import Room, Location, Department
from rest_framework.exceptions import PermissionDenied


class UserPermission(BasePermission):
    """
    User directory and self-service profile authorization.

    Rules:
    - Users may view themselves.
    - Users may update themselves.
    - Scoped user directory access requires users.view.
    - No admin-level writes are allowed here.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        # Self profile access
        if obj == user:
            return True

        # Directory read access
        if request.method in SAFE_METHODS:
            return AccessService.has_permission(
                user,
                "users.view",
            )

        # Self update only
        if request.method in [
            "PUT",
            "PATCH",
        ]:
            return user == obj

        return False


class UserPlacementPermission(
    ScopedPermission,
):
    """
    User placement authorization.

    Permission checks are handled by AccessService
    through ScopedPermission.

    Object-level scope checks are delegated to
    ScopeService so users can only manage placements
    within their assigned room/location/department scope.
    """

    permission_map = {
        "GET": "user_placements.view",
        "POST": "user_placements.create",
        "PUT": "user_placements.update",
        "PATCH": "user_placements.update",
        "DELETE": "user_placements.delete",
    }

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        room = getattr(
            obj,
            "room",
            None,
        )

        if not room:
            return False

        return (
            self.has_permission(
                request,
                view,
            )
            and ScopeService.can_access_room(
                active_role,
                room,
            )
        )
    

class AdminUpdateUserPermission(BasePermission):
    """
    Allows scoped admins to update user demographic info.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.method in ["PATCH", "PUT"]
        )

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "active_role", None)

        if not role:
            return False

        # SITE_ADMIN can edit anyone
        if role.role == "SITE_ADMIN":
            return True

        # Only admin roles
        if role.role not in [
            "DEPARTMENT_ADMIN",
            "LOCATION_ADMIN",
            "ROOM_ADMIN",
        ]:
            return False

        return is_user_in_scope(role, obj)



class UserProfilePermission( ScopedPermission):

    permission_map = {
        "GET": "users.view",
    }

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if obj == request.user:
            return True

        if not active_role:
            return False

        return (
            self.has_permission(
                request,
                view,
            )
            and UserScopeService.can_access_user(
                active_role,
                obj,
            )
        )
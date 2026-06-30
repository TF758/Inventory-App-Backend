# myapp/permissions/users.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from access.permissions.scoped import ScopedPermission
from access.services.scope import ScopeService, UserScopeService
from access.permissions.base import RequiresPermission
from access.services.access import AccessService
from core.permissions.helpers import is_user_in_scope
from users.models.roles import RoleAssignment
from .constants import ROLE_HIERARCHY



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

class RoleAssignmentPermission(
    ScopedPermission,
):
    """
    Role assignment authorization.

    Permission checks are handled by AccessService
    through ScopedPermission.

    Scope checks determine whether the acting role
    may view or interact with the target role
    assignment's department/location/room scope.

    Role governance (who may assign which roles)
    remains delegated to RoleGovernanceService /
    ensure_permission until the legacy hierarchy
    migration is completed.
    """

    permission_map = {
        "GET": "role_assignments.view",
        "POST": "role_assignments.create",
        "PUT": "role_assignments.update",
        "PATCH": "role_assignments.update",
        "DELETE": "role_assignments.delete",
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
        active_role = getattr(
        request.user,
        "active_role",
        None,
    )

        if not active_role:
            return False

        return (
            self.has_permission(
                request,
                view,
            )
            and ScopeService.can_access_role_assignment(
                active_role,
                obj,
            )
        )
    
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
    

class FullUserCreatePermission(
    RequiresPermission,
):
    required_permission = (
        "users.full_create"
    )
        
# class FullUserCreatePermission(BasePermission):
#     """
#     Permission for FullUserCreateView.

#     Rules:
#     - SITE_ADMIN: allowed
#     - DEPARTMENT_ADMIN: allowed
#     - LOCATION_ADMIN: denied
#     - ROOM_ADMIN: denied
#     - VIEWER / no role: denied
#     """

#     def has_permission(self, request, view):
#         if not request.user.is_authenticated:
#             return False

#         active = getattr(request.user, "active_role", None)
#         if not active:
#             return False

#         # Explicit allow-list (DO NOT use hierarchy here)
#         return active.role in [
#             "SITE_ADMIN",
#             "DEPARTMENT_ADMIN",
#         ]

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

class CanViewUserProfile(BasePermission):
    """
    Permission to view a user profile.
    """

    def has_permission(self, request, view):
        """
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):

        requester = request.user
        target_user = obj

        if requester == target_user:
            return True

        active_role = getattr(requester, "active_role", None)
        if not active_role:
            return False

        if active_role.role == "SITE_ADMIN":
            return True

        return is_user_in_scope(admin_role=active_role, target_user=target_user, )


class UserProfilePermission( ScopedPermission, ):

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
# authorization/base_permissions.py

from rest_framework.permissions import (
    SAFE_METHODS,
    BasePermission,
)

from authorization.services import (
    get_active_role,
    user_has_permission,
)
from core.permissions.helpers import is_in_scope


class ScopedPermission(BasePermission):

    permission_map = {}

    def get_permission_code(self, request):
        return self.permission_map.get(request.method)

    def has_permission(self, request, view):
        if (
            not request.user
            or not request.user.is_authenticated
        ):
            return False

        permission_code = self.get_permission_code(
            request
        )

        if not permission_code:
            return False

        return user_has_permission(
            request.user,
            permission_code,
        )

    def get_scope_object(self, obj):
        return getattr(obj, "room", None)

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        role = get_active_role(request.user)

        if not role:
            return False

        if role.role == "SITE_ADMIN":
            return True

        scope_obj = self.get_scope_object(obj)

        if not scope_obj:
            return False

        return is_in_scope(
            role,
            room=scope_obj,
        )

class RequiresPermission(BasePermission):
    """
    Base DRF permission class for database-backed permissions.

    Usage:
        class CanCreateAsset(RequiresPermission):
            required_permission = "assets.create"
    """

    required_permission = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        permission_code = self.get_required_permission(view)

        if not permission_code:
            return False

        return user_has_permission(
            request.user,
            permission_code,
        )

    def get_required_permission(self, view):
        return getattr(
            view,
            "required_permission",
            self.required_permission,
        )


class RequiresAnyPermission(BasePermission):
    """
    Allows access if the user has at least one permission.

    Usage:
        class SomeView(APIView):
            required_permissions = [
                "assets.view",
                "assets.update",
            ]
    """

    required_permissions = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        permission_codes = self.get_required_permissions(view)

        if not permission_codes:
            return False

        return any(
            user_has_permission(request.user, code)
            for code in permission_codes
        )

    def get_required_permissions(self, view):
        return getattr(
            view,
            "required_permissions",
            self.required_permissions,
        )


class RequiresAllPermissions(BasePermission):
    """
    Allows access only if the user has every listed permission.
    """

    required_permissions = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        permission_codes = self.get_required_permissions(view)

        if not permission_codes:
            return False

        return all(
            user_has_permission(request.user, code)
            for code in permission_codes
        )

    def get_required_permissions(self, view):
        return getattr(
            view,
            "required_permissions",
            self.required_permissions,
        )
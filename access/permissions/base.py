from rest_framework.permissions import BasePermission

from access.services.access import (
    AccessService,
)

class RequiresPermission(BasePermission):
    required_permission = None
    required_permissions = None

    def get_required_permissions(
        self,
        request,
        view,
    ):
        permissions = getattr(
            view,
            "required_permissions",
            self.required_permissions,
        )

        if permissions:
            return list(permissions)

        permission = getattr(
            view,
            "required_permission",
            self.required_permission,
        )

        if permission:
            return [permission]

        return []

    def has_permission(
        self,
        request,
        view,
    ):
        if not request.user or not request.user.is_authenticated:
            return False

        permission_codes = self.get_required_permissions(
            request,
            view,
        )

        if not permission_codes:
            return False

        return all(
            AccessService.has_permission(
                request.user,
                permission_code,
            )
            for permission_code in permission_codes
        )
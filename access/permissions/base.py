from rest_framework.permissions import BasePermission

from access.services.access import (
    AccessService,
)


class RequiresPermission(BasePermission):

    required_permission = None

    def get_required_permission(
        self,
        request,
        view,
    ):
        return getattr(
            view,
            "required_permission",
            self.required_permission,
        )

    def has_permission(
        self,
        request,
        view,
    ):
        if not request.user.is_authenticated:
            return False

        permission_code = self.get_required_permission(
            request,
            view,
        )

        if not permission_code:
            return False

        return AccessService.has_permission(
            request.user,
            permission_code,
        )
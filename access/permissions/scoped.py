from access.permissions.base import (
    RequiresPermission,
)


class ScopedPermission(RequiresPermission):
    permission_map = {}

    def get_required_permission(
        self,
        request,
        view,
    ):
        return self.permission_map.get(
            request.method
        )

    def has_permission(self, request, view):
        required_permission = self.get_required_permission(
            request,
            view,
        )

        result = super().has_permission(
            request,
            view,
        )
        return result
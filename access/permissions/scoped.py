from access.permissions.base import (
    RequiresPermission,
)


class ScopedPermission(RequiresPermission):
    permission_map = {}

    def get_required_permissions(
        self,
        request,
        view,
    ):
        permission = self.permission_map.get(
            request.method
        )

        if isinstance(permission, (list, tuple, set)):
            return list(permission)


        if permission:
            return [permission]

        return super().get_required_permissions(
            request,
            view,
        )
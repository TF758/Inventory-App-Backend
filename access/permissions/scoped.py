from access.permissions.base import (
    RequiresPermission,
)


class ScopedPermission(
    RequiresPermission
):

    permission_map = {}

    def get_required_permission(
        self,
        request,
        view,
    ):
        return self.permission_map.get(
            request.method
        )
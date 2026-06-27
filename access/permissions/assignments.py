

from inventory.access.permissions.scoped import ScopedPermission
from inventory.access.services.scope import ScopeService


class AssignmentPermission(ScopedPermission):

    permission_map = {
        "list": "assignments.view",
        "retrieve": "assignments.view",
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

        return (
            self.has_permission(
                request,
                view,
            )
            and ScopeService.can_access_assignment(
                active_role,
                obj,
            )
        )

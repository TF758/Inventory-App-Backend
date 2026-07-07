

from access.permissions.scoped import ScopedPermission
from access.services.scope import ScopeService
from django.conf import settings
from rest_framework.exceptions import PermissionDenied

class AssignmentPermission(
    ScopedPermission,
):
    """
    Assignment authorization.

    Permission capability is handled by ScopedPermission.
    Object scope is delegated to ScopeService.
    """

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

        if not self.has_permission(
            request,
            view,
        ):
            return False

        return ScopeService.can_access_assignment(
            active_role,
            obj,
        )
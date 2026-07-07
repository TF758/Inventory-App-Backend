from access.permissions.scoped import ScopedPermission
from access.services.scope import ScopeService


class RoleAssignmentPermission(
    ScopedPermission,
):
    """
    Role assignment authorization.

    Permission checks are handled by AccessService
    through ScopedPermission.

    Object-level scope checks are delegated to
    ScopeService.

    Role hierarchy, assignment constraints and
    governance are enforced separately through
    HierarchyService and RoleGovernanceService.
    """

    permission_map = {
        # CRUD
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
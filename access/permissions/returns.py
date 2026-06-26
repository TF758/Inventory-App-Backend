from access.services.scope import ScopeService
from access.permissions.scoped import ScopedPermission


class ReturnRequestPermission(ScopedPermission):
    """
    Return request authorization.

    Permission checks are handled by AccessService
    through ScopedPermission.

    Object-level scope checks are delegated to
    ScopeService.
    """

    permission_map = {
        "list": "returns.view",
        "retrieve": "returns.view",
        "pending": "returns.view",

        "approve": "returns.process",
        "deny": "returns.process",
        "process": "returns.process",
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
            and ScopeService.can_access_return_request(
                active_role,
                obj,
            )
        )
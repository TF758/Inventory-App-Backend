from rest_framework.exceptions import PermissionDenied
from authorization.helpers import is_in_scope
from authorization.permissions.base_permissions import ScopedPermission




class RoleAssignmentPermission( ScopedPermission ):

    permission_map = {
        "GET": "role_assignments.view",
        "POST": "role_assignments.create",
        "PUT": "role_assignments.update",
        "PATCH": "role_assignments.update",
        "DELETE": "role_assignments.delete",
    }





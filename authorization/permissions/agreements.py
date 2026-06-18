

from inventory.authorization.permissions.base_permissions import RequiresPermission, ScopedPermission
from inventory.authorization.services import user_has_permission
from rest_framework.permissions import BasePermission 

class AgreementPermission(ScopedPermission):
    """
    Permission class for agreement management.
    """

    permission_map = {
        "GET": "agreements.view",
        "POST": "agreements.create",
        "PUT": "agreements.update",
        "PATCH": "agreements.update",
        "DELETE": "agreements.delete",
    }

    def has_object_permission( self, request, view, obj, ):
        return True
    


class AgreementCoveragePermission( ScopedPermission ):
    """
    Agreement coverage management.

    """

    permission_map = {
        "GET": "agreements.view",
        "POST": "agreements.update",
        "PUT": "agreements.update",
        "PATCH": "agreements.update",
        "DELETE": "agreements.update",
    }

    def has_object_permission( self, request, view, obj, ):
        return True

class AgreementItemPermission( BasePermission ):

    action_permission_map = {
        "list": "agreements.view",
        "retrieve": "agreements.view",
        "attach": "agreements.attach_items",
        "detach": "agreements.detach_items",
    }

    def has_permission( self, request, view, ):
        if ( not request.user or not request.user.is_authenticated ):
            return False

        permission_code = (
            self.action_permission_map.get(
                view.action
            )
        )

        if not permission_code:
            return False

        return user_has_permission(
            request.user,
            permission_code,
        )

    def has_object_permission( self, request, view, obj, ):
        return True
    


class AgreementLifecyclePermission( RequiresPermission ):
    required_permission = "agreements.update"
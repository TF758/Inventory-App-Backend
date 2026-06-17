from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from inventory.authorization.services import get_active_role
from inventory.core.permissions.helpers import has_asset_custody_scope


class ReturnRequestScopePermission(BasePermission):
    """
    Validates that return requests fall within
    the user's custody scope.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        return True

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        role = get_active_role(
            request.user
        )

        if not role:
            return False

        if hasattr(obj, "items"):
            items = obj.items.all()

        elif hasattr(obj, "room"):
            items = [obj]

        else:
            return False

        for item in items:

            if not has_asset_custody_scope(
                role,
                item.room,
            ):
                raise PermissionDenied(
                    (
                        "Return request contains "
                        "assets outside your jurisdiction."
                    )
                )

        return True
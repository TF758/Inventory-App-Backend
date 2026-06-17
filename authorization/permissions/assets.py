

from authorization.permissions.base_permissions import RequiresPermission, ScopedPermission
from authorization.services import get_active_role
from core.permissions.helpers import has_asset_custody_scope
from rest_framework.permissions import ( BasePermission, )

from inventory.assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue


class AssetPermission(ScopedPermission):

    permission_map = {
        "GET": "assets.view",
        "POST": "assets.create",
        "PUT": "assets.update",
        "PATCH": "assets.update",
        "DELETE": "assets.delete",
    }

    def get_scope_object(self, obj):

        room = getattr(obj, "room", None)

        if hasattr(obj, "equipment") and obj.equipment:
            room = obj.equipment.room

        return room

class AssetCustodyScopePermission( BasePermission ):
    """
    Shared object-level custody scope validation.
    Replacing legacy CanManageAssetCustody
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
        asset,
    ):
        role = get_active_role(
            request.user
        )

        if not role:
            return False

        return has_asset_custody_scope(
            role,
            asset,
        )

class CanUseAsset(RequiresPermission):
    """
    Allows users to record usage only for assets
    currently assigned/issued to themselves.
    """

    required_permission = "assets.use"

    def has_object_permission(self, request, view, obj):

        if isinstance(obj, ConsumableIssue):
            return obj.user_id == request.user.id

        if isinstance(obj, AccessoryAssignment):
            return obj.user_id == request.user.id

        return False
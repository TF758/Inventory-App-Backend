

from authorization.permissions.base_permissions import ScopedPermission



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
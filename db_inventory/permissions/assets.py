# myapp/permissions/assets.py
from rest_framework.permissions import BasePermission
from .constants import ROLE_HIERARCHY
from .helpers import has_hierarchy_permission, is_in_scope

class AssetPermission(BasePermission):

    """Use t0 manage permission for physical assets such as:
    Equipment, Component, Accessories, Consumables ect"""

    method_role_map = {
        "GET": "ROOM_VIEWER",
        "POST": "ROOM_CLERK",
        "PUT": "ROOM_ADMIN",
        "PATCH": "ROOM_ADMIN",
        "DELETE": "ROOM_ADMIN",
    }

    def has_permission(self, request, view):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False
        if active_role.role == "SITE_ADMIN":
            return True
        return has_hierarchy_permission(active_role.role, required_role)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False
        if active_role.role == "SITE_ADMIN":
            return True
        return (
            has_hierarchy_permission(active_role.role, required_role)
            and is_in_scope(active_role, room=obj.room)
        )

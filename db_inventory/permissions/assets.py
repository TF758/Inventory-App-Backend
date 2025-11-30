# myapp/permissions/assets.py
from rest_framework.permissions import BasePermission
from .constants import ROLE_HIERARCHY
from .helpers import has_hierarchy_permission, is_in_scope, is_viewer_role
from ..models import Room


class AssetPermission(BasePermission):
    """
    Permission class for asset-related models:
    Equipment, Component, Accessories, Consumables, etc.

    - VIEWER roles cannot modify assets.
    - Other roles can modify according to hierarchy and scope.
    """

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

        # SITE_ADMIN bypasses all
        if active_role.role == "SITE_ADMIN":
            return True

        # Block VIEWER roles from any write operation
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        # Hierarchy check
        if not has_hierarchy_permission(active_role.role, required_role):
            return False

        # Scope check for POST (new objects)
        if request.method == "POST":
            room_id = request.data.get("room")
            if not room_id:
                return False
            room = Room.objects.filter(public_id=room_id).first()
            if not room:
                return False
            if not is_in_scope(active_role, room=room):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block VIEWER roles from write operations
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        # Determine the room for scope (supports Equipment, Component, etc.)
        room_for_scope = getattr(obj, "room", None)
        if hasattr(obj, "equipment") and obj.equipment:
            room_for_scope = obj.equipment.room

        # Hierarchy + scope check
        return (
            has_hierarchy_permission(active_role.role, required_role)
            and is_in_scope(active_role, room=room_for_scope)
        )
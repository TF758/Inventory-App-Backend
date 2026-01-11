from rest_framework.permissions import BasePermission
from db_inventory.models.asset_assignment import EquipmentAssignment
from .constants import ROLE_HIERARCHY
from .helpers import get_active_role, has_asset_custody_scope, has_hierarchy_permission, is_admin_role, is_in_scope, is_viewer_role
from db_inventory.models.site import Department, Location, Room
from rest_framework.exceptions import PermissionDenied

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
        "PUT": "ROOM_CLERK",
        "PATCH": "ROOM_CLERK",
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

class CanManageAssetCustody(BasePermission):
    """
    Permission to assign / unassign / reassign equipment.
    """

    message = "You do not have permission to manage this equipment."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, equipment):
        role = get_active_role(request.user)
        if not role:
            return False

        # Must be admin role
        if not is_admin_role(role.role):
            return False

        return has_asset_custody_scope(role, equipment)

class HasAssignmentScopePermission(BasePermission):
    """
    Permission for viewing equipment assignments.

    Rules:
    - Requires active role
    - SITE_ADMIN bypasses all checks
    - Viewer roles are denied
    - Active role must cover the requested scope object
      (department / location / room)
    """

    message = "You do not have permission to view equipment assignments for this scope."

    def has_permission(self, request, view):
        role = get_active_role(request.user)
        if not role:
            return False

        # SITE_ADMIN bypass
        if role.role == "SITE_ADMIN":
            return True

        # Viewer roles are blocked
        if is_viewer_role(role.role):
            return False

        # Resolve scope object from URL
        public_id = view.kwargs.get("public_id")
        if not public_id:
            return False

        department = location = room = None

        # Try resolving in order of hierarchy
        department = Department.objects.filter(public_id=public_id).first()
        if not department:
            location = Location.objects.filter(public_id=public_id).first()
        if not location and not department:
            room = Room.objects.filter(public_id=public_id).first()

        if not any([department, location, room]):
            raise PermissionDenied("Invalid scope identifier.")

        # Pure scope coverage check
        return is_in_scope(
            role,
            room=room,
            location=location,
            department=department,
        )

class CanViewEquipmentAssignments(BasePermission):
    """
    Permissions for EquipmentAssignmentViewSet.

    - list: SITE_ADMIN only
    - retrieve: admins whose active role covers the equipment's room
    """

    message = "You do not have permission to view this equipment assignment."

    def has_permission(self, request, view):
        role = get_active_role(request.user)
        if not role:
            return False

        # LIST endpoint → SITE_ADMIN only
        if view.action == "list":
            return role.role == "SITE_ADMIN"

        # For retrieve, defer to object-level permission
        return True

    def has_object_permission(self, request, view, obj: EquipmentAssignment):
        role = get_active_role(request.user)
        if not role:
            return False

        # SITE_ADMIN bypass
        if role.role == "SITE_ADMIN":
            return True

        # Viewer roles blocked
        if is_viewer_role(role.role):
            return False

        equipment = obj.equipment
        if not equipment or not equipment.room:
            return False

        # Pure scope coverage via equipment room
        return is_in_scope(
            role,
            room=equipment.room,
            location=equipment.room.location if equipment.room else None,
            department=(
                equipment.room.location.department
                if equipment.room and equipment.room.location
                else None
            ),
        )
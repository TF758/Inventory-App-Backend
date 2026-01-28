from rest_framework.permissions import BasePermission
from db_inventory.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment
from .constants import ROLE_HIERARCHY
from .helpers import get_active_role, has_asset_custody_scope, has_hierarchy_permission, is_admin_role, is_in_scope, is_viewer_role
from db_inventory.models.site import Department, Location, Room
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS


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
        

        print(request.user, getattr(request.user, "active_role", None))

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True


        if request.method in SAFE_METHODS:
            return True

        # WRITE: viewers can never write
        if is_viewer_role(active_role.role):
            return False

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return has_hierarchy_permission(active_role.role, required_role)

    def has_object_permission(self, request, view, obj):
            active_role = getattr(request.user, "active_role", None)
            if not active_role:
                return False

            # SITE_ADMIN bypass
            if active_role.role == "SITE_ADMIN":
                return True

            # Determine room for scope (supports nested assets)
            room_for_scope = getattr(obj, "room", None)
            if hasattr(obj, "equipment") and obj.equipment:
                room_for_scope = obj.equipment.room

            # READ: must be in scope
            if request.method in SAFE_METHODS:
                return True

            # WRITE: viewers blocked (defensive)
            if is_viewer_role(active_role.role):
                return False

            required_role = self.method_role_map.get(request.method)
            if not required_role:
                return False

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
        active_role = get_active_role(request.user)

        if not active_role:
            return False

        if active_role.role == "SITE_ADMIN":
            return True
        
        # return true for admins
        if is_admin_role(active_role.role):
            return True
        
        return False

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

class CanSelfReturnAsset(BasePermission):
    """
    Allows a user to self-return assets they personally hold.
    Explicitly disallows admin roles to prevent bypassing admin flows.
    """

    message = "Admins must use the admin return endpoint."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = get_active_role(request.user)
        if not role:
            return False

        # Explicitly block admin roles
        return not is_admin_role(role.role)

class CanUseAsset(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ConsumableIssue):
            return obj.user_id == request.user.id

        if isinstance(obj, AccessoryAssignment):
            return obj.user_id == request.user.id

        return False

class CanReportConsumableLoss(BasePermission):
    """
    Allows:
    - users to report loss on their own open issues
    - admins to report loss on any issue in scope
    
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    

class CanUpdateEquipmentStatus(BasePermission):
    """
    Permission to allow updating equipment status.

    Rules:
    - SITE_ADMIN: always allowed
    - Admin role + in-scope equipment: allowed
    - Non-admin but current assignee: allowed
    """

    def has_object_permission(self, request, view, equipment):
        # Only applies to write methods
        if request.method not in ("PATCH", "PUT"):
            return True

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # 1. SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # 2. Admin role + scope
        if (
            is_admin_role(active_role.role)
            and is_in_scope(active_role, room=getattr(equipment, "room", None))
        ):
            return True

        # 3. Assigned user (non-admin allowed)
        assignment = getattr(equipment, "active_assignment", None)
        if assignment and assignment.returned_at is None:
            return assignment.user_id == request.user.id

        return False
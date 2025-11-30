# myapp/permissions/users.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .constants import ROLE_HIERARCHY
from .helpers import is_in_scope, has_hierarchy_permission, ensure_permission, get_active_role
from ..utils import user_can_access_role
from db_inventory.models import Room, Location, Department


class UserPermission(BasePermission):
    """
    Permission class for User objects.
    Enforces department-level scope via active_role and can be later extended
    to use UserLocation for multi-department inference.
    """

    method_role_map = {
        "GET": "DEPARTMENT_VIEWER",
        "POST": "DEPARTMENT_ADMIN",
        "PUT": "DEPARTMENT_ADMIN",
        "PATCH": "DEPARTMENT_ADMIN",
        "DELETE": "DEPARTMENT_ADMIN",
    }

    def has_permission(self, request, view):
        # All authenticated users can GET (list/retrieve)
        if request.method == "GET":
            return request.user.is_authenticated

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        required_role = self.method_role_map.get(request.method)
        return has_hierarchy_permission(active_role.role, required_role)

    def has_object_permission(self, request, view, obj):
        user = request.user
        active_role = getattr(user, "active_role", None)

        # Always allow a user to access themselves
        if user == obj:
            return True

        # No role, cannot access others
        if not active_role:
            return False

        # Superuser or SITE_ADMIN bypass
        if user.is_superuser or active_role.role == "SITE_ADMIN":
            return True

        # --- READ-ONLY access ---
        if request.method in SAFE_METHODS:
            target_role = getattr(obj, "active_role", None)
            room = getattr(target_role, "room", None) if target_role else None
            location = getattr(target_role, "location", None) if target_role else None
            department = getattr(target_role, "department", None) if target_role else None

            # Scope check: allow if target user is within scope
            return is_in_scope(active_role, room=room, location=location, department=department)

        # --- WRITE access ---
        required_role = self.method_role_map.get(request.method)
        target_role = getattr(obj, "active_role", None)
        if not target_role:
            return False

        return (
            has_hierarchy_permission(active_role.role, required_role)
            and is_in_scope(
                active_role,
                room=target_role.room,
                location=target_role.location,
                department=target_role.department,
            )
        )
    
class RolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        active = get_active_role(user)

        if user.is_superuser or (active and active.role == "SITE_ADMIN"):
            return True

        if getattr(view, "action", None) in ["list", "retrieve"]:
            return True

        if request.method == "POST" and active and active.role == "ROOM_ADMIN":
            new_role = request.data.get("role")
            if new_role not in ["ROOM_VIEWER", "ROOM_CLERK"]:
                return False

        if active and active.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN"]:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        active = get_active_role(user)

        if user.is_superuser or (active and active.role == "SITE_ADMIN"):
            return True

        if request.method in SAFE_METHODS:
            result = is_in_scope(active, obj.room, obj.location, obj.department)
            return result

        # Write operations: check NEW incoming data instead of old obj
        new_role_data = request.data.get("role", obj.role)
        if isinstance(new_role_data, dict):
            new_role = new_role_data.get("role")  # <-- extract string
            new_room = None
            new_location = None
            new_department = None

            # Convert public_id to actual model instances
            if "room" in new_role_data and new_role_data["room"]:
                new_room = Room.objects.filter(public_id=new_role_data["room"]).first()
            if "location" in new_role_data and new_role_data["location"]:
                new_location = Location.objects.filter(public_id=new_role_data["location"]).first()
            if "department" in new_role_data and new_role_data["department"]:
                new_department = Department.objects.filter(public_id=new_role_data["department"]).first()
        else:
            new_role = new_role_data
            new_room = new_location = new_department = None

        if active.role == "ROOM_ADMIN" and new_role not in ["ROOM_VIEWER", "ROOM_CLERK"]:
            return False

        try:
            ensure_permission(
                user,
                new_role,
                new_room or getattr(obj, "room", None),
                new_location or getattr(obj, "location", None),
                new_department or getattr(obj, "department", None)
            )
            return True
        except Exception as e:
            return False

class UserLocationPermission(BasePermission):
    method_role_map = {
        "GET": "ROOM_VIEWER",    # minimum role to read
        "HEAD": "ROOM_VIEWER",
        "OPTIONS": "ROOM_VIEWER",
        "POST": "ROOM_ADMIN",    # minimum role to write
        "PUT": "ROOM_ADMIN",
        "PATCH": "ROOM_ADMIN",
        "DELETE": "ROOM_ADMIN",
    }

    def has_permission(self, request, view):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # Site admin can always do anything
        if active_role.role == "SITE_ADMIN":
            return True

        # Explicitly block any viewer roles from write methods
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and "_VIEWER" in active_role.role:
            return False

        # Otherwise, check hierarchy
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # Site admin can always do anything
        if active_role.role == "SITE_ADMIN":
            return True

        # Block viewers from write methods
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and "_VIEWER" in active_role.role:
            return False

        # Check hierarchy
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False
        if ROLE_HIERARCHY.get(active_role.role, 0) < ROLE_HIERARCHY.get(required_role, 0):
            return False

        # Scope check for the object
        if "ROOM" in active_role.role:
            return is_in_scope(active_role, room=obj.room)
        elif "LOCATION" in active_role.role:
            return is_in_scope(active_role, location=obj.room.location)
        elif "DEPARTMENT" in active_role.role:
            return is_in_scope(active_role, department=obj.room.location.department)

        return False
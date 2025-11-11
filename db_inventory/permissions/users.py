# myapp/permissions/users.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .constants import ROLE_HIERARCHY
from .helpers import is_in_scope, has_hierarchy_permission, ensure_permission, get_active_role
from ..utils import user_can_access_role

class UserPermission(BasePermission):
    method_role_map = {
        "GET": "DEPARTMENT_VIEWER",
        "POST": "DEPARTMENT_ADMIN",
        "PUT": "DEPARTMENT_ADMIN",
        "PATCH": "DEPARTMENT_ADMIN",
        "DELETE": "DEPARTMENT_ADMIN",
    }

    def has_permission(self, request, view):
        # All authenticated users can view (list/retrieve)
        if request.method == "GET":
            return request.user.is_authenticated

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        if active_role.role == "SITE_ADMIN":
            return True

        required_role = self.method_role_map.get(request.method)
        return has_hierarchy_permission(active_role.role, required_role)

    def has_object_permission(self, request, view, obj):
        user = request.user
        active_role = getattr(user, "active_role", None)

        # Always allow self
        if user == obj:
            return True

        # If no role, can't access anyone else
        if not active_role:
            return False

        # Superuser or site admin can access anyone
        if user.is_superuser or active_role.role == "SITE_ADMIN":
            return True

        # --- READ-ONLY ACCESS ---
        if request.method in SAFE_METHODS:
            target_role = getattr(obj, "active_role", None)

            # handle users without active_role
            room = getattr(target_role, "room", None)
            location = getattr(target_role, "location", None)
            department = getattr(target_role, "department", None)

            # Viewer/Clerk/Admin roles can read anyone within their scope
            return is_in_scope(active_role, room=room, location=location, department=department)

        # --- WRITE ACCESS (admin-level only) ---
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

        if active and active.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN"]:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        active = get_active_role(user)

        if request.method in SAFE_METHODS:
            result = is_in_scope(active, getattr(obj, "room", None), getattr(obj, "location", None), getattr(obj, "department", None))
            return result

        if not active:
            return False

        try:
            ensure_permission(user, obj.role, getattr(obj, "room", None), getattr(obj, "location", None), getattr(obj, "department", None))
            return True
        except Exception as e:
            return False

class UserLocationPermission(BasePermission):
    method_role_map = {
        "GET": "ROOM_VIEWER",
        "POST": "ROOM_ADMIN",
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
        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        required_role = self.method_role_map.get(request.method)
        if not active_role or not required_role:
            return False
        if active_role.role == "SITE_ADMIN":
            return True
        if ROLE_HIERARCHY.get(active_role.role, 0) < ROLE_HIERARCHY.get(required_role, 0):
            return False
        return is_in_scope(active_role, room=obj.room)

# myapp/permissions/users.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .constants import ROLE_HIERARCHY
from .helpers import is_in_scope, has_hierarchy_permission
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
        if request.method == "GET":
            return True
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False
        if active_role.role == "SITE_ADMIN":
            return True
        required_role = self.method_role_map.get(request.method)
        return has_hierarchy_permission(active_role.role, required_role)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if request.user == obj:
            return True
        if active_role and active_role.role in ("SITE_ADMIN", "DEPARTMENT_ADMIN"):
            return True
        required_role = self.method_role_map.get(request.method)
        target_role = getattr(obj, "active_role", None)
        if not target_role:
            return False
        if request.method == "GET":
            return is_in_scope(active_role,
                               room=target_role.room,
                               location=target_role.location,
                               department=target_role.department)
        return (has_hierarchy_permission(active_role.role, required_role)
                and is_in_scope(active_role,
                                room=target_role.room,
                                location=target_role.location,
                                department=target_role.department))

class RolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, "role", None) == "SITE_ADMIN":
            return True
        if view.action in ["list", "retrieve"]:
            return True
        active = getattr(user, "active_role", None)
        if active and active.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN", "SITE_ADMIN"]:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return user_can_access_role(user, obj)
        active = getattr(user, "active_role", None)
        if active and active.role in ["SITE_ADMIN", "DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN"]:
            return user_can_access_role(user, obj)
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

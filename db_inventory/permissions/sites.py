from rest_framework.permissions import BasePermission
from .constants import ROLE_HIERARCHY
from db_inventory.models import Department, Location

class RoomPermission(BasePermission):
    method_role_map = {
        "POST": "LOCATION_ADMIN",
        "PUT": "ROOM_ADMIN",
        "PATCH": "ROOM_ADMIN",
        "DELETE": "LOCATION_ADMIN",
        "GET": "ROOM_VIEWER",
    }

    def has_permission(self, request, view):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False
        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False
        if active_role.role == "SITE_ADMIN":
            return True
        if active_role.room:
            return active_role.room == obj
        if active_role.location:
            return active_role.location == obj.location
        if active_role.department:
            return active_role.department == obj.location.department
        return False


    
class LocationPermission(BasePermission):
    """
    Permission for Location objects based on the user's active_role:
      - All methods enforce role hierarchy and object scope
    """

    method_role_map: dict[str, str] = {
        "GET": "LOCATION_VIEWER",      
        "POST": "DEPARTMENT_ADMIN",
        "PUT": "LOCATION_ADMIN",
        "PATCH": "LOCATION_ADMIN",
        "DELETE": "DEPARTMENT_ADMIN",
    }

    def has_permission(self, request, view) -> bool:
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # POST: check department from request data
        if request.method == "POST":
            department_id = request.data.get("department")
            department = Department.objects.filter(pk=department_id).first() if department_id else None
            if not department:
                return False
            if active_role.role == "SITE_ADMIN":
                return True
            if active_role.department and active_role.department == department:
                return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)
            return False

        # Other methods: just check hierarchy (object-level still enforced later)
        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj: Location) -> bool:
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        if active_role.role == "SITE_ADMIN":
            return True

        # Object-level scope enforcement
        if active_role.department and obj.department == active_role.department:
            return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(self.method_role_map.get(request.method, ""), 0)
        if active_role.location and obj == active_role.location:
            return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(self.method_role_map.get(request.method, ""), 0)

        # Room-level roles cannot access locations
        return False


class DepartmentPermission(BasePermission):
    """
    Permission for Department objects based on the user's active_role:
      - All methods enforce hierarchy and object scope
    """

    method_role_map = {
        "GET": "DEPARTMENT_VIEWER",     # minimum role to view departments
        "POST": "SITE_ADMIN",
        "PUT": "DEPARTMENT_ADMIN",
        "PATCH": "DEPARTMENT_ADMIN",
        "DELETE": "SITE_ADMIN",
    }

    def has_permission(self, request, view):
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # POST requires SITE_ADMIN and department is not relevant yet
        if request.method == "POST":
            return active_role.role == "SITE_ADMIN"

        # All other methods: enforce hierarchy
        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypasses everything
        if active_role.role == "SITE_ADMIN":
            return True

        # Object-level scope: department active role must match
        if active_role.department and obj == active_role.department:
            return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

        # Lower-level roles (location/room) cannot access departments
        return False
    
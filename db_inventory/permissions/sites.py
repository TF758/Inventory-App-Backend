from rest_framework.permissions import BasePermission
from .constants import ROLE_HIERARCHY
from db_inventory.models import Department, Location
from .helpers import has_hierarchy_permission, is_in_scope, check_permission

class RoomPermission(BasePermission):
    method_role_map = {
        "POST": "LOCATION_ADMIN",
        "PUT": "ROOM_ADMIN",
        "PATCH": "ROOM_ADMIN",
        "DELETE": "LOCATION_ADMIN",
        "GET": "ROOM_VIEWER",
    }

    def has_permission(self, request, view):
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False
        return check_permission(request.user, required_role)


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
      - Enforces role hierarchy and object scope
      - SITE_ADMIN bypasses all checks
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

        # SITE_ADMIN bypasses everything
        if active_role.role == "SITE_ADMIN":
            return True

        # For POST, extract department from request data
        if request.method == "POST":
            dept_id = request.data.get("department")
            if not dept_id:
                return False
            department = Department.objects.filter(public_id=dept_id).first()
            if not department:
                return False

            # DEPARTMENT_ADMIN: bypass hierarchy but respect department
            if active_role.role == "DEPARTMENT_ADMIN":
                return is_in_scope(active_role, department=department)

            # Other roles: use full check
            return check_permission(request.user, required_role, department=department)

        # For GET/PUT/PATCH/DELETE, rely on object-level permission
        return True

    def has_object_permission(self, request, view, obj: Location) -> bool:
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypasses everything
        if active_role.role == "SITE_ADMIN":
            return True

        required_role = self.method_role_map.get(request.method)

        # DEPARTMENT_ADMIN bypasses hierarchy but still needs to be in their department
        if active_role.role == "DEPARTMENT_ADMIN":
            return is_in_scope(active_role, location=obj)  # only check scope

        # For other roles, use full check_permission (hierarchy + scope)
        return check_permission(request.user, required_role, location=obj)


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
    
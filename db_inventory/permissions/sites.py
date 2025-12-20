from rest_framework.permissions import BasePermission
from .constants import ROLE_HIERARCHY
from db_inventory.models.site import Department, Location, Room
from .helpers import  is_in_scope, check_permission, is_viewer_role, is_admin_role, has_hierarchy_permission


class RoomPermission(BasePermission):
    """
    Permission class for Room objects.
    Handles ROOM_VIEWER, ROOM_ADMIN, LOCATION_ADMIN, DEPARTMENT_ADMIN, SITE_ADMIN.
    """

    method_role_map = {
        "POST": "LOCATION_ADMIN",   # create room
        "PUT": "ROOM_ADMIN",        # update room
        "PATCH": "ROOM_ADMIN",      # partial update
        "DELETE": "LOCATION_ADMIN", # delete room
        "GET": "ROOM_VIEWER",       # view room
    }

    def has_permission(self, request, view):
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block VIEWER roles from write methods
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        # POST (create room)
        if request.method == "POST":
            loc_id = request.data.get("location")
            if not loc_id:
                return False
            location = Location.objects.filter(public_id=loc_id).first()
            if not location:
                return False

            # Scope check for DEPARTMENT_ADMIN or LOCATION_ADMIN
            if active_role.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN"]:
                return is_in_scope(active_role, location=location)

            # ROOM_ADMIN cannot create rooms
            return False

        # Other methods defer to object-level permissions
        return True

    def has_object_permission(self, request, view, obj: Room):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        method = request.method

        # GET: viewers and admins can view rooms in scope
        if method == "GET":
            if is_viewer_role(active_role.role) or is_admin_role(active_role.role):
                return is_in_scope(active_role, room=obj)
            return False

        # PUT/PATCH: ROOM_ADMIN, LOCATION_ADMIN, DEPARTMENT_ADMIN
        if method in ["PUT", "PATCH"]:
            if active_role.role in ["ROOM_ADMIN", "LOCATION_ADMIN", "DEPARTMENT_ADMIN"]:
                return is_in_scope(active_role, room=obj)
            return False

        # DELETE: LOCATION_ADMIN or DEPARTMENT_ADMIN
        if method == "DELETE":
            if active_role.role in ["LOCATION_ADMIN", "DEPARTMENT_ADMIN"]:
                return is_in_scope(active_role, room=obj)
            return False

        return False


    
class LocationPermission(BasePermission):
    """
    Permission class for Location objects.
    
    - VIEWER roles can only read (GET/HEAD/OPTIONS)
    - Other roles operate according to hierarchy and object scope
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

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block viewers from any write operation
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        # For POST, check department scope
        if request.method == "POST":
            dept_id = request.data.get("department")
            if not dept_id:
                return False
            department = Department.objects.filter(public_id=dept_id).first()
            if not department:
                return False

            # DEPARTMENT_ADMIN can create locations within their department
            if active_role.role == "DEPARTMENT_ADMIN":
                return is_in_scope(active_role, department=department)

            # Other roles: rely on hierarchy check
            return has_hierarchy_permission(active_role.role, required_role)

        # For GET, PUT, PATCH, DELETE: defer to object-level checks
        return True

    def has_object_permission(self, request, view, obj: Location) -> bool:
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block viewers from any write operation
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        # DEPARTMENT_ADMIN can operate within department scope
        if active_role.role == "DEPARTMENT_ADMIN":
            return is_in_scope(active_role, location=obj)

        # LOCATION_ADMIN can operate within their location
        if active_role.role == "LOCATION_ADMIN":
            return is_in_scope(active_role, location=obj)

        # Other roles: hierarchy check
        return has_hierarchy_permission(active_role.role, required_role)


class DepartmentPermission(BasePermission):
    """
    Permission class for Department objects.

    - VIEWER roles can only GET
    - Other roles operate according to hierarchy and object scope
    - SITE_ADMIN bypasses all checks
    """

    method_role_map = {
        "GET": "DEPARTMENT_VIEWER",     # minimum role to view departments
        "POST": "SITE_ADMIN",           # create new department
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

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block VIEWER roles from any write operation
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        # POST requires SITE_ADMIN explicitly
        if request.method == "POST":
            return active_role.role == "SITE_ADMIN"

        # Other methods: enforce hierarchy
        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block VIEWER roles from write operations
        if request.method in ("PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        # Object-level scope: department active role must match
        if active_role.department and obj == active_role.department:
            return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

        # Lower-level roles (location/room) cannot access departments
        return False
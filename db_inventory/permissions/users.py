# myapp/permissions/users.py
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .constants import ROLE_HIERARCHY
from .helpers import is_admin_role, is_in_scope, has_hierarchy_permission, ensure_permission, get_active_role, is_viewer_role
from db_inventory.models.site import Room, Location, Department
from db_inventory.models.roles import RoleAssignment
from rest_framework.exceptions import PermissionDenied

ROLE_ASSIGNMENT_RULES = {
    "ROOM_ADMIN": ["ROOM_VIEWER", "ROOM_CLERK"],
    "LOCATION_ADMIN": ["ROOM_VIEWER", "ROOM_CLERK","ROOM_ADMIN", "LOCATION_VIEWER"],
    "DEPARTMENT_ADMIN": [
        "ROOM_VIEWER", "ROOM_CLERK", "ROOM_ADMIN",
        "LOCATION_VIEWER", "LOCATION_ADMIN",
        "DEPARTMENT_VIEWER",
    ],
    # SITE_ADMIN or superuser are unrestricted, so no rule needed
}


class UserPermission(BasePermission):
    """
    Permission class for User objects.

    Rules:
    - All authenticated users may view users
    - Users may edit themselves
    - Admins may edit users within scope
    - Only SITE_ADMIN and DEPARTMENT_ADMIN may delete users
    - Deletion is scope-restricted and self-deletion is forbidden
    """

    # ----------------------
    # REQUEST-LEVEL
    # ----------------------

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        active_role = getattr(user, "active_role", None)

        # READ is open to all authenticated users
        if request.method in SAFE_METHODS:
            return True

        # CREATE user
        if request.method == "POST":
            return (
                active_role
                and active_role.role in ["SITE_ADMIN", "DEPARTMENT_ADMIN"]
            )

        # UPDATE / DELETE handled at object level
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        active_role = getattr(user, "active_role", None)

        # ------------------
        # SELF ACCESS
        # ------------------
        if user == obj:
            if request.method == "DELETE":
                return False
            return True

        if not active_role:
            return False

        # SITE ADMIN
        if active_role.role == "SITE_ADMIN":
            return True

        # ------------------
        # 🔒 LOCKING USERS (SPECIAL CASE)
        # ------------------
        if request.method in ["PUT", "PATCH"] and "is_locked" in request.data:
            return active_role.role == "DEPARTMENT_ADMIN"

        # ------------------
        # READ
        # ------------------
        if request.method in SAFE_METHODS:
            target_role = getattr(obj, "active_role", None)
            if not target_role:
                return False

            return is_in_scope(
                active_role,
                room=target_role.room,
                location=target_role.location,
                department=target_role.department,
            )

        # ------------------
        # WRITE / DELETE
        # ------------------
        if active_role.role != "DEPARTMENT_ADMIN":
            return False

        target_role = getattr(obj, "active_role", None)
        if not target_role:
            return False

        if not is_in_scope(
            active_role,
            room=target_role.room,
            location=target_role.location,
            department=target_role.department,
        ):
            return False

        if request.method == "DELETE":
            return True

        return True
    



class RolePermission(BasePermission):
    """
    Permission class for RoleAssignment objects.

    Enforces:
    - SITE_ADMIN full bypass
    - Viewer roles have no access
    - Admins may CREATE / UPDATE / DELETE roles
      they could have CREATED in the same scope
    - No same-rank or upward role manipulation
    - Peer admins are invisible via queryset filtering
    """

    # -------------------------
    # REQUEST-LEVEL PERMISSION
    # -------------------------

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        active = get_active_role(user)

        # SITE_ADMIN bypass
        if active and active.role == "SITE_ADMIN":
            return True

        # Viewers cannot do anything
        if not active or is_viewer_role(active.role):
            return False

        # READ allowed (scoped later)
        if request.method in SAFE_METHODS:
            return True

        # -------------------------
        # CREATE (POST) — CRITICAL FIX
        # -------------------------
        if request.method == "POST":
            requested_role = request.data.get("role")
            if not requested_role:
                return False

            # ❌ Prevent same-rank or upward role creation
            if ROLE_HIERARCHY.get(requested_role, 0) >= ROLE_HIERARCHY.get(active.role, 0):
                return False

            return True

        # UPDATE / DELETE — defer to object-level
        return active.role in [
            "ROOM_ADMIN",
            "LOCATION_ADMIN",
            "DEPARTMENT_ADMIN",
        ]

    # -------------------------
    # OBJECT-LEVEL PERMISSION
    # -------------------------

    def has_object_permission(self, request, view, obj: RoleAssignment):
        user = request.user
        active = get_active_role(user)

        if not active:
            return False

        # SITE_ADMIN bypass
        if active.role == "SITE_ADMIN":
            return True

        # -------------------------
        # READ
        # -------------------------
        if request.method in SAFE_METHODS:
            return is_in_scope(
                active,
                room=obj.room,
                location=obj.location,
                department=obj.department,
            )

        # -------------------------
        # WRITE (PUT / PATCH / DELETE)
        # -------------------------

        # Cannot touch same-rank or higher EXISTING roles
        if ROLE_HIERARCHY.get(obj.role, 0) >= ROLE_HIERARCHY.get(active.role, 0):
            return False

        # Determine intended new role
        new_role = request.data.get("role", obj.role)

        # Prevent same-rank or upward role manipulation
        new_role = request.data.get("role", obj.role)
        if ROLE_HIERARCHY.get(new_role, 0) >= ROLE_HIERARCHY.get(active.role, 0):
            return False


        # Determine intended new scope (treat update as reassignment)
        new_room = None
        new_location = None
        new_department = None

        if "room" in request.data:
            new_room = Room.objects.filter(public_id=request.data["room"]).first()

        if "location" in request.data:
            new_location = Location.objects.filter(public_id=request.data["location"]).first()

        if "department" in request.data:
            new_department = Department.objects.filter(public_id=request.data["department"]).first()

        try:
            ensure_permission(
                user,
                new_role,
                room=new_room,
                location=new_location,
                department=new_department,
            )
            return True
        except PermissionDenied:
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

        # Block viewers from any write operations
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
            return False

        # Check role hierarchy
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # Site admin bypass
        if active_role.role == "SITE_ADMIN":
            return True

        # Block viewers from write operations
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_viewer_role(active_role.role):
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
    

class FullUserCreatePermission(BasePermission):
    """
    Permission for FullUserCreateView.

    Rules:
    - SITE_ADMIN: allowed
    - DEPARTMENT_ADMIN: allowed
    - LOCATION_ADMIN: denied
    - ROOM_ADMIN: denied
    - VIEWER / no role: denied
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        active = getattr(request.user, "active_role", None)
        if not active:
            return False

        # Explicit allow-list (DO NOT use hierarchy here)
        return active.role in [
            "SITE_ADMIN",
            "DEPARTMENT_ADMIN",
        ]
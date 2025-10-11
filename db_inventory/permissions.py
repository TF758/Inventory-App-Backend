from typing import Optional
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from .models import RoleAssignment, User, Room, Location, Department, Equipment, Component, Accessory, Consumable
from django.db.models import Q


# Role hierarchy: higher numbers mean more power
ROLE_HIERARCHY = {
    # Room roles
    "ROOM_VIEWER": 0,
    "ROOM_CLERK": 1,
    "ROOM_ADMIN": 2,

    # Location roles
    "LOCATION_VIEWER": 3,
    "LOCATION_ADMIN": 4,

    # Department roles
    "DEPARTMENT_VIEWER": 5,
    "DEPARTMENT_ADMIN": 6,

    
    "SITE_ADMIN": 99,
}

def get_active_role(user: User) -> Optional[RoleAssignment]:
    """Return the user's active role assignment (or None)."""
    return user.active_role

def get_user_roles(user: User):
    """Return all role assignments for a given user."""
    return RoleAssignment.objects.filter(user=user)


def has_hierarchy_permission(user_role: str, required_role: str) -> bool:
    """Check if one role is at least as high as another in the hierarchy."""
    if user_role == "SITE_ADMIN":
        return True
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, -1)


def is_in_scope(
    role_assignment: RoleAssignment,
    room: Optional[Room] = None,
    location: Optional[Location] = None,
    department: Optional[Department] = None,
) -> bool:
    """Check whether a role assignment applies to the given object scope."""

    if not role_assignment:
        return False

    if role_assignment.role == "SITE_ADMIN":
        return True

    if department and role_assignment.department == department:
        return True

    if location:
        if role_assignment.location == location:
            return True
        if role_assignment.department and location.department == role_assignment.department:
            return True

    if room:
        if role_assignment.room == room:
            return True
        if role_assignment.location and room.location == role_assignment.location:
            return True

    return False


def check_permission(
    user: User,
    required_role: str,
    room: Optional[Room] = None,
    location: Optional[Location] = None,
    department: Optional[Department] = None,
) -> bool:
    """
    Returns True if the user's active role has permission for the given object.
    """
    role = user.active_role
    if not role:
        return False

    if has_hierarchy_permission(role.role, required_role):
        return is_in_scope(role, room=room, location=location, department=department)

    return False


def ensure_permission(
    user: User,
    required_role: str,
    room: Optional[Room] = None,
    location: Optional[Location] = None,
    department: Optional[Department] = None,
):
    """Raise PermissionDenied if active role doesn't meet the requirement."""
    if not check_permission(user, required_role, room, location, department):
        raise PermissionDenied(
            detail=f"Active role lacks {required_role} permission for this resource."
        )


def filter_queryset_by_scope(user: User, queryset, model_class):
    """
    Restrict a queryset to only objects within the user's active role scope.
    Site admins always see everything.
    """
    active_role = user.active_role

    if not active_role:
        return queryset.none()  # no active role, no access

    # SITE_ADMIN sees all
    if active_role.role == "SITE_ADMIN":
        return queryset

    q = Q()

    if model_class == Room:
        if active_role.room:
            q |= Q(pk=active_role.room.pk)
        elif active_role.location:
            q |= Q(location=active_role.location)
        elif active_role.department:
            q |= Q(location__department=active_role.department)

    elif model_class == Location:
        if active_role.room:
        # Room-level roles cannot see any locations
            return queryset.none()
        if active_role.location:
            q |= Q(pk=active_role.location.pk)
        elif active_role.department:
            q |= Q(department=active_role.department)

    elif model_class == Department:
        if active_role.room or active_role.location:
        # Room or location roles cannot see departments
            return queryset.none()
        if active_role.department:
            q |= Q(pk=active_role.department.pk)


    elif model_class in (Equipment, Accessory, Consumable):
        if active_role.room:
            q |= Q(room=active_role.room)
        elif active_role.location:
            q |= Q(room__location=active_role.location)
        elif active_role.department:
            q |= Q(room__location__department=active_role.department)

    elif model_class == Component:
        if active_role.room:
             q |= Q(equipment__room=active_role.room)
        elif active_role.location:
            q |= Q(equipment__room__location=active_role.location)
        elif active_role.department:
            q |= Q(equipment__room__location__department=active_role.department)


    elif model_class == User:
        if active_role.room:
            q |= Q(role_assignments__room=active_role.room)
        elif active_role.location:
            q |= Q(role_assignments__location=active_role.location)
        elif active_role.department:
            q |= Q(role_assignments__department=active_role.department)
    return queryset.filter(q).distinct()


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

        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # check hierarchy
        return ROLE_HIERARCHY.get(active_role.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        if active_role.role == "SITE_ADMIN":
            return True

        # enforce scope
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
        "GET": "ROOM_VIEWER",     # minimum role to view departments
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
    

class AssetPermission(BasePermission):
    """
    Generic permission class for Room-scoped assets (Equipment, Accessory, Consumable).
    Enforces:
      - Role hierarchy (who can do what)
      - Scope (where they can do it)
    """

    # Default permission levels for CRUD operations
    method_role_map = {
        "GET": "ROOM_VIEWER",      # can list / view 
        "POST": "ROOM_CLERK",      # can create items in their room
        "PUT": "ROOM_ADMIN",       # can modify items
        "PATCH": "ROOM_ADMIN",
        "DELETE": "ROOM_ADMIN",    # can delete items
    }

    def has_permission(self, request, view):
        """
        Called for non-object-level checks (e.g., list, create).
        """
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        # SITE_ADMIN always allowed
        if active_role.role == "SITE_ADMIN":
            return True

        # For POST (creation), ensure they’re creating within scope (handled in perform_create)
        return has_hierarchy_permission(active_role.role, required_role)

    def has_object_permission(self, request, view, obj):
        """
        Called for object-level checks (retrieve, update, delete).
        """
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypass
        if active_role.role == "SITE_ADMIN":
            return True

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        # Check both hierarchy and scope
        return (
            has_hierarchy_permission(active_role.role, required_role)
            and is_in_scope(active_role, room=obj.room)
        )
    

class UserPermission(BasePermission):
    """
    Permission for managing users based on the request.user's active role.
    """

    method_role_map = {
        "GET": "DEPARTMENT_VIEWER",    # Can list/retrieve users in scope
        "POST": "DEPARTMENT_ADMIN",    # Can create users in their department
        "PUT": "DEPARTMENT_ADMIN",     # Can update users in scope
        "PATCH": "DEPARTMENT_ADMIN",
        "DELETE": "DEPARTMENT_ADMIN",  # Can delete users in scope
    }

    def has_permission(self, request, view):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
           return False

        required_role = self.method_role_map.get(request.method)
        if not required_role:
             return False

        # SITE_ADMIN can always proceed
        if active_role.role == "SITE_ADMIN":
            return True

        # Check hierarchy
        if not has_hierarchy_permission(active_role.role, required_role):
             return False

        return True

    def has_object_permission(self, request, view, obj):
        active_role = getattr(request.user, "active_role", None)
        if not active_role:
            return False

        # SITE_ADMIN bypasses
        if active_role.role == "SITE_ADMIN":
            return True

        required_role = self.method_role_map.get(request.method)

        # Check hierarchy
        if not has_hierarchy_permission(active_role.role, required_role):
            return False

        # Object-level permission
        target_role = getattr(obj, "active_role", None)

        # Allow GET if target user has no active_role
        if request.method == "GET" and target_role is None:
            return True

        # For other methods, deny if no target_role
        if not target_role:
            return False

        # Check scope
        if not is_in_scope(
            active_role,
            room=target_role.room,
            location=target_role.location,
            department=target_role.department
        ):
            return False

        return True
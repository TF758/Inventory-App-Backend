from typing import Optional
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from .models import RoleAssignment, User, Room, Location, Department
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
    Returns True if the user has permission to act on the given object.
    """
    for role in get_user_roles(user):
        if has_hierarchy_permission(role.role, required_role):
            if is_in_scope(role, room=room, location=location, department=department):
                return True
    return False


def ensure_permission(
    user: User,
    required_role: str,
    room: Optional[Room] = None,
    location: Optional[Location] = None,
    department: Optional[Department] = None,
):
    """
    Raises PermissionDenied if the user does not meet the required permission.
    """
    if not check_permission(user, required_role, room=room, location=location, department=department):
        raise PermissionDenied(detail=f"User lacks {required_role} permission for this resource.")


def filter_queryset_by_scope(user: User, queryset, model_class):
    """
    Restrict a queryset to only objects within the user's assigned scope.
    Site admins always see everything.
    """
    role_assignments = get_user_roles(user)

    # Site admins bypass all filters
    if any(r.role == "SITE_ADMIN" for r in role_assignments):
        return queryset

    q = Q()
    for role in role_assignments:
        if model_class == Room:
            if role.room:
                q |= Q(pk=role.room.pk)
            elif role.location:
                q |= Q(location=role.location)
            elif role.department:
                q |= Q(location__department=role.department)

        elif model_class == Location:
            if role.location:
                q |= Q(pk=role.location.pk)
            elif role.department:
                q |= Q(department=role.department)

        elif model_class == Department:
            if role.department:
                q |= Q(pk=role.department.pk)

    return queryset.filter(q).distinct()


class RoomPermission(BasePermission):
    """
    Custom DRF permission for Room objects.
    Enforces hierarchy + scope rules:
      - ROOM_CLERK exist for minor updates
      - ROOM_VIEWER has view
      - ROOM_ADMIN can edit
      - LOCATION_ADMIN+ can delete/create
    """

    method_role_map = {
        "GET": "ROOM_VIEWER",      # now explicitly Room Viewer
        "HEAD": "ROOM_VIEWER",
        "OPTIONS": "ROOM_VIEWER",
        "POST": "LOCATION_ADMIN",
        "PUT": "ROOM_ADMIN",
        "PATCH": "ROOM_ADMIN",
        "DELETE": "LOCATION_ADMIN",
    }

    def has_permission(self, request, view):
        """Check general permissions before object exists (e.g. list, create)."""
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        location = None
        if request.method == "POST":
            location_id = request.data.get("location")
            if location_id:
                try:
                    location = Location.objects.get(pk=location_id)
                except Location.DoesNotExist:
                    return False  # invalid location -> deny

        return check_permission(
            user=request.user,
            required_role=required_role,
            location=location,
        )

    def has_object_permission(self, request, view, obj):
        """Check permissions for object-level operations (retrieve/update/delete)."""
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return check_permission(
            user=request.user,
            required_role=required_role,
            room=obj,
        )

class LocationPermission(BasePermission):
    """
    Custom DRF permission for Location objects.
    Rules:
      - ROOM_CLERK has no rights on locations
      - LOCATION_ADMIN can view and update their location
      - DEPARTMENT_ADMIN can create and delete locations
      - SITE_ADMIN bypasses all checks
    """

    method_role_map = {
        "GET": "LOCATION_VIEWER",     # switched to Location Viewer
        "HEAD": "LOCATION_VIEWER",
        "OPTIONS": "LOCATION_VIEWER",
        "POST": "DEPARTMENT_ADMIN",
        "PUT": "LOCATION_ADMIN",
        "PATCH": "LOCATION_ADMIN",
        "DELETE": "DEPARTMENT_ADMIN",
    }

    def has_permission(self, request, view):
        """Check before object exists (e.g., POST)."""
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        if request.method == "POST":
            # Department must be in request data for create
            department_id = request.data.get("department")
            return check_permission(
                user=request.user,
                required_role=required_role,
                department_id=department_id,
            )

        # For list, let higher roles pass (SITE_ADMIN, DEPT_ADMIN)
        return check_permission(user=request.user, required_role=required_role)

    def has_object_permission(self, request, view, obj):
        """Check when operating on an existing Location."""
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return check_permission(
            user=request.user,
            required_role=required_role,
            location=obj,
            department=obj.department,
        )
    


class DepartmentPermission(BasePermission):
    """
    Custom DRF permission for Department objects.
    Rules:
      - DEPARTMENT_ADMIN can view/list/update their department
      - SITE_ADMIN can create, delete
      - Lower roles cannot act on departments
    """

    method_role_map = {
        "GET": "DEPARTMENT_VIEWER",     # switched to Department Viewer
        "HEAD": "DEPARTMENT_VIEWER",
        "OPTIONS": "DEPARTMENT_VIEWER",
        "POST": "SITE_ADMIN",
        "PUT": "DEPARTMENT_ADMIN",
        "PATCH": "DEPARTMENT_ADMIN",
        "DELETE": "SITE_ADMIN",
        }

    def has_permission(self, request, view):
        """Check before object exists (e.g., POST)."""
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        # For POST, check if user is SiteAdmin
        if request.method == "POST":
            return check_permission(user=request.user, required_role=required_role)

        # For listing, allow DepartmentAdmin and above
        return check_permission(user=request.user, required_role=required_role)

    def has_object_permission(self, request, view, obj):
        """Check when operating on an existing Department."""
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return check_permission(
            user=request.user,
            required_role=required_role,
            department=obj,
        )
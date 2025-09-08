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
        if active_role.location:
            q |= Q(pk=active_role.location.pk)
        elif active_role.department:
            q |= Q(department=active_role.department)

    elif model_class == Department:
        if active_role.department:
            q |= Q(pk=active_role.department.pk)

    return queryset.filter(q).distinct()


class RoomPermission(BasePermission):
    """
    Permission for Room objects:
      - GET is open to all authenticated users 
      - POST/PUT/PATCH/DELETE enforce role hierarchy
    """

    method_role_map = {
        "POST": "LOCATION_ADMIN",
        "PUT": "ROOM_ADMIN",
        "PATCH": "ROOM_ADMIN",
        "DELETE": "LOCATION_ADMIN",
    }

    def has_permission(self, request, view):
        # Allow GET/HEAD/OPTIONS for everyone
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        # Only check hierarchy for write actions
        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False  

        return check_permission(request.user, required_role)
        

    def has_object_permission(self, request, view, obj):
        # GET/HEAD/OPTIONS are open, but object-level scope still enforced
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

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
    Permission for Location objects:
      - GET/HEAD/OPTIONS are open 
      - POST/PUT/PATCH/DELETE enforce role hierarchy
    """

    method_role_map = {
        "POST": "DEPARTMENT_ADMIN",
        "PUT": "LOCATION_ADMIN",
        "PATCH": "LOCATION_ADMIN",
        "DELETE": "DEPARTMENT_ADMIN",
    }

    def has_permission(self, request, view):
        # Allow GET/HEAD/OPTIONS for all
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        
         # POST needs department from request data
        if request.method == "POST":
            department_id = request.data.get("department")
            department = (
                Department.objects.filter(pk=department_id).first()
                if department_id else None
            )
            return check_permission(
                user=request.user,
                required_role=required_role,
                department=department,
            )

        # PUT/PATCH/DELETE will be object-level checked
        return check_permission(request.user, required_role)

    def has_object_permission(self, request, view, obj):
        # GET/HEAD/OPTIONS are open, but scope is filtered in queryset
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

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
    Permission for Department objects:
      - GET/HEAD/OPTIONS open 
      - POST/DELETE restricted to SITE_ADMIN
      - PUT/PATCH restricted to DEPARTMENT_ADMIN and SITE_ADMIN
    """

    method_role_map = {
        "POST": "SITE_ADMIN",
        "PUT": "DEPARTMENT_ADMIN",
        "PATCH": "DEPARTMENT_ADMIN",
        "DELETE": "SITE_ADMIN",
    }

    def has_permission(self, request, view):
        # Allow GET/HEAD/OPTIONS for all authenticated users
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return check_permission(request.user, required_role)

    def has_object_permission(self, request, view, obj):
        # GET/HEAD/OPTIONS are open, actual data filtered via queryset
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        required_role = self.method_role_map.get(request.method)
        if not required_role:
            return False

        return check_permission(
            user=request.user,
            required_role=required_role,
            department=obj,
        )
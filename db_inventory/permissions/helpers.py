# myapp/permissions/helpers.py
from typing import Optional
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from db_inventory.models import RoleAssignment, User, Room, Location, Department, Equipment, Component, Accessory, Consumable
from .constants import ROLE_HIERARCHY

def get_active_role(user: User) -> Optional[RoleAssignment]:
    return getattr(user, "active_role", None)

def get_user_roles(user: User):
    return RoleAssignment.objects.filter(user=user)

def has_hierarchy_permission(user_role: str, required_role: str) -> bool:
    if user_role == "SITE_ADMIN":
        return True
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, -1)

def is_in_scope(role_assignment: RoleAssignment,
                room: Optional[Room] = None,
                location: Optional[Location] = None,
                department: Optional[Department] = None) -> bool:
    if not role_assignment:
        return False
    if role_assignment.role == "SITE_ADMIN":
        return True

    # Department level
    if department:
        if role_assignment.department == department:
            return True
        if role_assignment.location and role_assignment.location.department == department:
            return True
        if role_assignment.room and role_assignment.room.location.department == department:
            return True

    # Location level
    if location:
        if role_assignment.location == location:
            return True
        if role_assignment.department and location.department == role_assignment.department:
            return True
        if role_assignment.room and role_assignment.room.location == location:
            return True

    # Room level
    if room:
        if role_assignment.room == room:
            return True
        if role_assignment.location and role_assignment.location == room.location:
            return True
        if role_assignment.department and room.location.department == role_assignment.department:
            return True

    return False

def check_permission(user: User, required_role: str,
                     room: Optional[Room] = None,
                     location: Optional[Location] = None,
                     department: Optional[Department] = None) -> bool:
    role = get_active_role(user)
    if not role:
        return False
    if has_hierarchy_permission(role.role, required_role):
        return is_in_scope(role, room, location, department)
    return False

def ensure_permission(user: User, required_role: str,
                      room: Optional[Room] = None,
                      location: Optional[Location] = None,
                      department: Optional[Department] = None):
    if not check_permission(user, required_role, room, location, department):
        raise PermissionDenied(f"Active role lacks {required_role} permission for this resource.")

def filter_queryset_by_scope(user: User, queryset, model_class):
    active_role = get_active_role(user)
    if not active_role:
        return queryset.none()

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
            return queryset.none()
        if active_role.location:
            q |= Q(pk=active_role.location.pk)
        elif active_role.department:
            q |= Q(department=active_role.department)

    elif model_class == Department:
        if active_role.room or active_role.location:
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

    elif model_class == RoleAssignment:
        if active_role.room:
            q |= Q(room=active_role.room)
        elif active_role.location:
            q |= Q(location=active_role.location) | Q(room__location=active_role.location)
        elif active_role.department:
            q |= (
                Q(department=active_role.department)
                | Q(location__department=active_role.department)
                | Q(room__location__department=active_role.department)
            )

    elif model_class.__name__ == "User":
        user_q = Q()
        if active_role.department:
            user_q |= Q(role_assignments__department=active_role.department)
            user_q |= Q(user_locations__room__location__department=active_role.department)
        elif active_role.location:
            user_q |= Q(role_assignments__location=active_role.location)
            user_q |= Q(user_locations__room__location=active_role.location)
        elif active_role.room:
            user_q |= Q(role_assignments__room=active_role.room)
            user_q |= Q(user_locations__room=active_role.room)

        if active_role.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN"]:
            user_q |= Q(active_role__isnull=True,
                        created_by__role_assignments__department=active_role.department)

        if active_role.role == "SITE_ADMIN":
            user_q |= Q()

        q |= user_q

    return queryset.filter(q).distinct()

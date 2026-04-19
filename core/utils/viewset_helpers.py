
from sites.models.sites import Department, Location, Room, UserPlacement
from users.models.users import User
from core.utils.constants import ADMIN_ROLES
from django.db.models import Q

def get_current_room_for_user(user):
    return (
        UserPlacement.objects
        .filter(user=user, is_current=True)
        .select_related("room__location__department")
        .first()
    )

def get_site_admins():
    """
    Return all global site admins.
    """
    return (
        User.objects
        .filter(role_assignments__role="SITE_ADMIN")
        .distinct()
    )


def get_admins_responsible_for_room(room):
    location = room.location
    department = location.department if location else None

    return User.objects.filter(
        role_assignments__role__in=ADMIN_ROLES
    ).filter(
        Q(role_assignments__room=room) |
        Q(role_assignments__location=location) |
        Q(role_assignments__department=department) |
        Q(role_assignments__role="SITE_ADMIN")
    ).distinct()



def get_admins_responsible_for_room(room):
    """
    Return users who have admin responsibility over the given room.
    """

    if not room:
        return get_site_admins()

    location = room.location
    department = location.department if location else None

    return (
        User.objects
        .filter(
            role_assignments__role__in=ADMIN_ROLES
        )
        .filter(
            Q(role_assignments__room=room) |
            Q(role_assignments__location=location) |
            Q(role_assignments__department=department) |
            Q(role_assignments__role="SITE_ADMIN")
        )
        .distinct())

def get_users_affected_by_site(site):
    """
    Return users whose *current* location is inside the given site object.

    Supports:
    - Room
    - Location
    - Department
    """

    if isinstance(site, Room):
        return (
            User.objects
            .filter(
                user_placements__room=site,
                user_placements__is_current=True,
            )
            .distinct()
        )

    if isinstance(site, Location):
        return (
            User.objects
            .filter(
                user_placements__room__location=site,
                user_placements__is_current=True,
            )
            .distinct()
        )

    if isinstance(site, Department):
        return (
            User.objects
            .filter(
                user_placements__room__location__department=site,
                user_placements__is_current=True,
            )
            .distinct()
        )

    return User.objects.none()

from django.db.models import Exists, OuterRef

def unallocated_users_queryset():
    current_location_exists = UserPlacement.objects.filter(
        user=OuterRef("pk"),
        is_current=True,
    )

    return User.objects.annotate(
        has_current_location=Exists(current_location_exists)
    ).filter(
        has_current_location=False,
        is_system_user=False,
    )
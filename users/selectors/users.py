from users.models import User
from django.db.models import Q
from django.utils import timezone


ADMIN_ROLES = [
    "DEPARTMENT_ADMIN",
    "LOCATION_ADMIN",
    "ROOM_ADMIN",
    "SITE_ADMIN",
]




def all_users_queryset():
    """
    Get all users.
    """
    return User.objects.all()


def active_users_queryset():
    """
    Return all active users
    """
    return  all_users_queryset().filter(
        is_active=True
    )

def human_users_queryset():
    """
    Non-system users.
    """
    return  all_users_queryset().filter(
        is_system_user=False
    )


def users_without_active_role_queryset():
    """
    Return users withotu an active role
    """
    return  human_users_queryset().filter(
        active_role__isnull=True,
        is_system_user=False,
    )

def system_users_queryset():
    """
    Users created for system/service purposes.
    """
    return all_users_queryset().filter(
        is_system_user=True
    )

def locked_users_queryset():
    """
    Users currently locked either permanently
    or through a temporary lock window.
    """
    return human_users_queryset().filter(
        Q(is_locked=True)
        | Q(locked_until__gt=timezone.now())
    )

def department_users_queryset(department):
    """
    Users currently placed within a department.
    """
    return User.objects.filter(
        user_placements__is_current=True,
        user_placements__room__location__department=department,
    ).distinct()

def department_admins_queryset(department):
    """
    Department admins including inherited location,
    room and site admins.
    """
    return (
        department_users_queryset(department)
        .filter(
            role_assignments__role__in=ADMIN_ROLES
        )
        .filter(
            Q(
                role_assignments__department=department
            )
            | Q(
                role_assignments__location__department=department
            )
            | Q(
                role_assignments__room__location__department=department
            )
            | Q(
                role_assignments__role="SITE_ADMIN"
            )
        )
        .distinct()
    )



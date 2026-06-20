# authorization/services/role_delegation.py
from rest_framework.exceptions import PermissionDenied
from authorization.helpers import get_active_role, invalidate_role_permission_cache, is_in_scope
from django.db import transaction
from authorization.models import Permission, Role, RolePermission


def can_manage_role_assignment( actor, assignment, ) -> bool:
    """
    Determines whether the actor may manage
    an existing role assignment.

    Prevents peer-admin and upward-admin
    modification.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True

    if not active_role.role_ref:
        return False

    if not assignment.role_ref:
        return False

    return (
        active_role.role_ref.level
        >
        assignment.role_ref.level
    )


def can_grant_role(
    actor,
    target_role,
) -> bool:
    """
    Prevent privilege escalation.

    Actor may only grant roles whose
    permissions are a subset of their own.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True

    if not active_role.role_ref:
        return False

    actor_permissions = {
        rp.permission.code
        for rp in active_role.role_ref.role_permissions.filter(
            enabled=True
        ).select_related("permission")
    }

    target_permissions = {
        rp.permission.code
        for rp in target_role.role_permissions.filter(
            enabled=True
        ).select_related("permission")
    }

    return target_permissions.issubset(
        actor_permissions
    )

def ensure_can_grant_role( actor, target_role, ):
    """
    Raises PermissionDenied if the actor
    may not delegate the target role.
    """

    if not can_grant_role( actor, target_role, ):
        raise PermissionDenied(
            "You may not assign a role containing permissions you do not possess."
        )



    
def can_assign_role( *, actor, target_role, room=None, location=None, department=None, ) -> bool:
    """
    Business validation for role assignment.

    Assumes endpoint capability checks have
    already been performed by RoleAssignmentPermission.
    """
    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True

    if not can_grant_role(
        actor,
        target_role,
    ):
        return False

    return is_in_scope(
        active_role,
        room=room,
        location=location,
        department=department,
    )

def can_update_role_assignment( *, actor, assignment, new_role=None, room=None, location=None, department=None, ) -> bool:
    """
    Business validation for role assignment updates.

    Assumes endpoint capability checks have
    already been performed by RoleAssignmentPermission.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True
    
    if not can_manage_role_assignment( actor, assignment ):
        return False

    if new_role:
        if not can_grant_role(
            actor,
            new_role,
        ):
            return False

    target_room = room or assignment.room
    target_location = location or assignment.location
    target_department = department or assignment.department

    return is_in_scope(
        active_role,
        room=target_room,
        location=target_location,
        department=target_department,
    )


def can_delete_role_assignment( *, actor, assignment, ) -> bool:
    """
    Business validation for role assignment deletion.

    Assumes endpoint capability checks have
    already been performed by RoleAssignmentPermission.
    """

    active_role = get_active_role(actor)

    if not active_role:
        return False

    if active_role.role == "SITE_ADMIN":
        return True
    
    if not can_manage_role_assignment( actor, assignment, ):
        return False

    return is_in_scope(
        active_role,
        room=assignment.room,
        location=assignment.location,
        department=assignment.department,
    )


def ensure_can_assign_role(**kwargs):
    if not can_assign_role(**kwargs):
        raise PermissionDenied(
            "You cannot assign roles in this scope."
        )


def ensure_can_update_role_assignment(**kwargs):
    if not can_update_role_assignment(**kwargs):
        raise PermissionDenied(
            "You cannot modify role assignments in this scope."
        )


def ensure_can_delete_role_assignment(**kwargs):
    if not can_delete_role_assignment(**kwargs):
        raise PermissionDenied(
            "You cannot delete role assignments in this scope."
        )
@transaction.atomic
def sync_role_permissions(
    *,
    role,
    permission_codes,
):
    desired_permissions = set(
        permission_codes
    )

    permissions = {
        permission.code: permission
        for permission in Permission.objects.filter(
            code__in=desired_permissions
        )
    }

    existing = {
        rp.permission.code: rp
        for rp in RolePermission.objects.filter(
            role=role
        ).select_related(
            "permission"
        )
    }

    # Enable/Create

    for code in desired_permissions:

        role_permission = existing.get(
            code
        )

        if role_permission:

            if not role_permission.enabled:

                role_permission.enabled = True

                role_permission.save(
                    update_fields=[
                        "enabled",
                        "updated_at",
                    ]
                )

        else:

            RolePermission.objects.create(
                role=role,
                permission=permissions[code],
                enabled=True,
            )

    # Disable removed

    for code, role_permission in (
        existing.items()
    ):

        if code not in desired_permissions:

            if role_permission.enabled:

                role_permission.enabled = False

                role_permission.save(
                    update_fields=[
                        "enabled",
                        "updated_at",
                    ]
                )

@transaction.atomic
def sync_permission_matrix(
    assignments,
):
    roles = {
        str(role.public_id): role
        for role in Role.objects.all()
    }

    for role_public_id, permission_codes in (
        assignments.items()
    ):

        role = roles[
            str(role_public_id)
        ]

        sync_role_permissions(
            role=role,
            permission_codes=permission_codes,
        )

    invalidate_role_permission_cache()
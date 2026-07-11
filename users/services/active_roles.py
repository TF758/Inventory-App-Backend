"""Active-role switching with scoped-cache invalidation."""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import PermissionDenied


from core.user_scope_cache import UserScopeCacheService
from users.models.roles import RoleAssignment
from users.models.users import User


class ActiveRoleService:
    @classmethod
    def switch_active_role(
        cls,
        *,
        user: User,
        role_public_id: str,
    ) -> RoleAssignment:
        role = (
            RoleAssignment.objects.select_related(
                "department",
                "location",
                "room",
            )
            .filter(
                public_id=role_public_id,
                user_id=user.pk,
            )
            .first()
        )

        if role is None:
            raise PermissionDenied(
                "Cannot activate a role that is not assigned to you."
            )

        old_active_role_id = user.active_role_id
        if old_active_role_id == role.pk:
            return role

        with transaction.atomic():
            user.active_role = role
            user.save(update_fields=["active_role"])

            UserScopeCacheService.invalidate_user_on_commit(
                user.public_id,
                reason=(
                    "active_role_changed:"
                    f"old_db_id={old_active_role_id}:"
                    f"new_public_id={role.public_id}"
                ),
            )

        return role

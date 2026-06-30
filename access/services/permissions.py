from collections import OrderedDict
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from access.models import  Permission, RolePermission
from core.models.sessions import UserSession
from users.models.roles import RoleAssignment


class PermissionMatrixService:
    """
    Service responsible for reading and updating
    the configurable permission matrix.

    The frontend treats permissions as a matrix of:

        Domain
            Permission
                Role -> Enabled

    Only configurable permissions are exposed here.

    Non-configurable permissions such as system-flow,
    site-admin-only, or ownership-based permissions are
    intentionally excluded from this matrix.
    """

    SYSTEM_ROLES = {
        "SITE_ADMIN",
    }

    @classmethod
    def configurable_roles(cls):
        return [
            (role, label)
            for role, label in RoleAssignment.ROLE_CHOICES
            if role not in cls.SYSTEM_ROLES
        ]

    @classmethod
    def get_matrix(cls):
        permissions = (
            Permission.objects
            .filter(
                is_configurable=True,
            )
            .prefetch_related(
                "role_permissions",
            )
            .order_by(
                "sort_order",
                "domain",
                "code",
            )
        )

        roles = [
            {
                "code": role,
                "name": label,
            }
            for role, label in cls.configurable_roles()
        ]

        valid_roles = {
            role["code"]
            for role in roles
        }

        domains = OrderedDict()

        for permission in permissions:
            if permission.domain not in domains:
                domains[permission.domain] = {
                    "code": permission.domain,
                    "name": permission.domain.replace(
                        "_",
                        " ",
                    ).title(),
                    "permissions": [],
                }

            assigned_roles = {
                role_permission.role
                for role_permission in permission.role_permissions.all()
                if role_permission.role in valid_roles
            }

            domains[
                permission.domain
            ]["permissions"].append({
                "code": permission.code,
                "name": permission.name,
                "description": permission.description,
                "scope_type": permission.scope_type,
                "sort_order": permission.sort_order,
                "roles": [
                    {
                        "role": role["code"],
                        "enabled": (
                            role["code"]
                            in assigned_roles
                        ),
                    }
                    for role in roles
                ],
            })

        return {
            "roles": roles,
            "domains": list(
                domains.values(),
            ),
        }

    @classmethod
    @transaction.atomic
    def update_matrix(
        cls,
        payload,
    ):
        permissions = (
            Permission.objects
            .filter(
                is_configurable=True,
            )
            .prefetch_related(
                "role_permissions",
            )
        )

        permission_lookup = {
            permission.code: permission
            for permission in permissions
        }

        valid_roles = {
            role
            for role, _
            in cls.configurable_roles()
        }

        created_count = 0
        deleted_count = 0

        for domain in payload.get(
            "domains",
            [],
        ):
            for item in domain.get(
                "permissions",
                [],
            ):
                permission_code = item.get(
                    "code",
                )

                permission = permission_lookup.get(
                    permission_code,
                )

                # Ignore unknown or non-configurable permissions.
                # Non-configurable permissions are intentionally
                # absent from permission_lookup.
                if not permission:
                    continue

                requested_roles = {
                    role_data.get("role")
                    for role_data in item.get(
                        "roles",
                        [],
                    )
                    if (
                        role_data.get("enabled")
                        and role_data.get("role") in valid_roles
                    )
                }

                existing_roles = {
                    role_permission.role
                    for role_permission in permission.role_permissions.all()
                    if role_permission.role in valid_roles
                }

                to_create = (
                    requested_roles
                    - existing_roles
                )

                to_delete = (
                    existing_roles
                    - requested_roles
                )

                if to_create:
                    RolePermission.objects.bulk_create(
                        [
                            RolePermission(
                                role=role,
                                permission=permission,
                            )
                            for role in to_create
                        ],
                        ignore_conflicts=True,
                    )

                    created_count += len(
                        to_create
                    )

                if to_delete:
                    deleted, _ = (
                        RolePermission.objects
                        .filter(
                            permission=permission,
                            role__in=to_delete,
                        )
                        .delete()
                    )

                    deleted_count += deleted

        matrix = cls.get_matrix()

        matrix["meta"] = {
            "changes": {
                "created": created_count,
                "deleted": deleted_count,
                "changed": (
                    created_count > 0
                    or deleted_count > 0
                ),
            },
        }

        return matrix


class PermissionMatrixSessionService:
    """
    Handles session revocation after permission matrix updates.

    Permission matrix updates are treated as a security boundary.
    When the matrix actually changes, active sessions are revoked
    so users reload a fresh permission context on next sign-in.

    The acting Site Admin is excluded so they are not kicked out
    immediately after saving.
    """

    @staticmethod
    def _normalize_session_id(
        session_id,
    ):
        if not session_id:
            return None

        try:
            return UUID(
                str(session_id),
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    @classmethod
    def revoke_after_matrix_update(
        cls,
        *,
        actor,
        current_session_id=None,
    ):
        current_session_uuid = cls._normalize_session_id(
            current_session_id,
        )

        sessions = (
            UserSession.objects
            .filter(
                status=UserSession.Status.ACTIVE,
            )
            .select_related(
                "user",
            )
        )

        # Keep the actor signed in.
        # This follows the product decision that the
        # active Site Admin should not be booted by
        # their own matrix update.
        if actor:
            sessions = sessions.exclude(
                user=actor,
            )

        # Defensive extra exclusion in case this method
        # is later reused without excluding the actor.
        if current_session_uuid:
            sessions = sessions.exclude(
                id=current_session_uuid,
            )

        affected_user_ids = list(
            sessions
            .values_list(
                "user_id",
                flat=True,
            )
            .distinct()
        )

        revoked_count = sessions.update(
            status=UserSession.Status.REVOKED,
        )

        User = get_user_model()

        affected_users = list(
            User.objects.filter(
                id__in=affected_user_ids,
            )
        )

        return {
            "revoked_count": revoked_count,
            "affected_user_ids": affected_user_ids,
            "affected_users": affected_users,
        }
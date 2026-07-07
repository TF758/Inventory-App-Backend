from access.models import RolePermission


class AccessService:

    @staticmethod
    def has_permission(
        user,
        permission_code: str,
    ) -> bool:

        active_role = getattr(
            user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        if active_role.role == "SITE_ADMIN":
            return True

        return RolePermission.objects.filter(
            role=active_role.role,
            permission__code=permission_code,
        ).exists()
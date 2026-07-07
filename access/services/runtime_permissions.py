from access.models import Permission, RolePermission


class RuntimePermissionService:
    """
    Returns runtime permission codes for the currently active role.

    This is used by the frontend permission context.
    It is not used for editing the permission matrix.
    """

    @classmethod
    def get_for_user(cls, user):
        active_role = getattr(
            user,
            "active_role",
            None,
        )

        if not active_role:
            return {
                "active_role": None,
                "permissions": [],
            }

        return {
            "active_role": cls.serialize_active_role(
                active_role,
            ),
            "permissions": cls.get_permission_codes(
                active_role,
            ),
        }

    @classmethod
    def get_permission_codes(cls, active_role):
        """
        SITE_ADMIN is not stored in RolePermission rows because it is
        not editable through the matrix.

        Non-site roles read from RolePermission.
        """

        if active_role.role == "SITE_ADMIN":
            return list(
                Permission.objects
                .order_by(
                    "sort_order",
                    "domain",
                    "code",
                )
                .values_list(
                    "code",
                    flat=True,
                )
            )

        return list(
            RolePermission.objects
            .filter(
                role=active_role.role,
            )
            .select_related(
                "permission",
            )
            .order_by(
                "permission__sort_order",
                "permission__domain",
                "permission__code",
            )
            .values_list(
                "permission__code",
                flat=True,
            )
        )

    @classmethod
    def serialize_active_role(cls, active_role):
        scope_type = cls.get_scope_type(
            active_role,
        )

        return {
            "public_id": active_role.public_id,
            "code": active_role.role,
            "name": active_role.get_role_display(),
            "scope_type": scope_type,
            "scope": cls.get_scope_payload(
                active_role,
            ),
        }

    @classmethod
    def get_scope_type(cls, active_role):
        if active_role.role == "SITE_ADMIN":
            return "SITE"

        if active_role.department_id:
            return "DEPARTMENT"

        if active_role.location_id:
            return "LOCATION"

        if active_role.room_id:
            return "ROOM"

        return None

    @classmethod
    def get_scope_payload(cls, active_role):
        if active_role.department_id:
            return {
                "type": "DEPARTMENT",
                "public_id": active_role.department.public_id,
                "name": active_role.department.name,
            }

        if active_role.location_id:
            return {
                "type": "LOCATION",
                "public_id": active_role.location.public_id,
                "name": active_role.location.name,
            }

        if active_role.room_id:
            return {
                "type": "ROOM",
                "public_id": active_role.room.public_id,
                "name": active_role.room.name,
            }

        if active_role.role == "SITE_ADMIN":
            return {
                "type": "SITE",
                "public_id": None,
                "name": "Entire Site",
            }

        return None
from inventory.access.services.scope import ScopeService


class RoleGovernanceService:
    ASSIGNABLE_ROLES = {
        "ROOM_ADMIN": {
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
        "LOCATION_ADMIN": {
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
        "DEPARTMENT_ADMIN": {
            "LOCATION_ADMIN",
            "LOCATION_VIEWER",
            "ROOM_ADMIN",
            "ROOM_CLERK",
            "ROOM_VIEWER",
        },
        "SITE_ADMIN": "__all__",
    }

    @classmethod
    def can_assign_role(
        cls,
        actor_role,
        target_role,
    ):
        if not actor_role or not target_role:
            return False

        allowed = cls.ASSIGNABLE_ROLES.get(
            actor_role.role
        )

        if allowed == "__all__":
            return True

        if not allowed:
            return False

        return target_role in allowed

    @staticmethod
    def can_assign_scope(
        actor_role,
        *,
        room=None,
        location=None,
        department=None,
    ):
        if not actor_role:
            return False

        if actor_role.role == "SITE_ADMIN":
            return True

        if room:
            return ScopeService.can_access_room(
                actor_role,
                room,
            )

        if location:
            return (
                actor_role.role in {
                    "LOCATION_ADMIN",
                    "DEPARTMENT_ADMIN",
                }
                and (
                    actor_role.location_id == location.id
                    or actor_role.department_id == location.department_id
                )
            )

        if department:
            return (
                actor_role.role == "DEPARTMENT_ADMIN"
                and actor_role.department_id == department.id
            )

        return False

    @classmethod
    def can_assign(
        cls,
        actor_role,
        target_role,
        *,
        room=None,
        location=None,
        department=None,
    ):
        return (
            cls.can_assign_role(
                actor_role,
                target_role,
            )
            and cls.can_assign_scope(
                actor_role,
                room=room,
                location=location,
                department=department,
            )
        )
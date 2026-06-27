from access.services.scope import ScopeService
from access.services.hierachy import HierarchyService


class RoleGovernanceService:
    """
    Governs role assignment and management.

    Responsibilities
    ----------------
    - Which roles an actor may assign/manage.
    - Whether the assignment scope is valid.
    - Delegates hierarchy validation to HierarchyService.
    """

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

    # =====================================================
    # Role Governance
    # =====================================================

    @classmethod
    def can_assign_role(
        cls,
        actor_role,
        target_role,
    ):
        if not actor_role or not target_role:
            return False

        allowed = cls.ASSIGNABLE_ROLES.get(
            actor_role.role,
        )

        if allowed == "__all__":
            return True

        if not allowed:
            return False

        return target_role in allowed

    # =====================================================
    # Scope Validation
    # =====================================================

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

        if room:

            if not HierarchyService.can_assign_to_room(
                actor_role.role,
            ):
                return False

            return ScopeService.can_access_room(
                actor_role,
                room,
            )

        if location:

            if not HierarchyService.can_assign_to_location(
                actor_role.role,
            ):
                return False

            return (
                actor_role.role == "SITE_ADMIN"
                or (
                    actor_role.department_id
                    == location.department_id
                )
            )

        if department:

            if not HierarchyService.can_assign_to_department(
                actor_role.role,
            ):
                return False

            return (
                actor_role.role == "SITE_ADMIN"
                or actor_role.department_id
                == department.id
            )

        return False

    # =====================================================
    # Combined Checks
    # =====================================================

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

    @classmethod
    def can_manage_assignment(
        cls,
        actor_role,
        assignment,
    ):
        if not actor_role:
            return False

        return (
            cls.can_assign_role(
                actor_role,
                assignment.role,
            )
            and cls.can_assign_scope(
                actor_role,
                room=assignment.room,
                location=assignment.location,
                department=assignment.department,
            )
        )
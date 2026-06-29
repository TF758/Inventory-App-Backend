
from access.services.scope import ScopeService
from access.services.hierachy import HierarchyService
from access.hierachy import MANAGES_ALL, ROLE_HIERARCHY_LIST


class RoleGovernanceService:
    """
    Governs role assignment and management.

    Responsibilities
    ----------------
    - Which roles an actor may assign/manage.
    - Whether the assignment scope is valid.
    - Delegates hierarchy placement validation to HierarchyService.

    Does NOT determine:
    - Permissions
    - Object visibility outside role governance
    """

    # =====================================================
    # Internal Helpers
    # =====================================================

    @staticmethod
    def _managed_roles(actor_role):
        if not actor_role:
            return set()

        config = ROLE_HIERARCHY_LIST.get(
            actor_role.role,
            {},
        )

        return config.get(
            "manages",
            set(),
        )

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

        allowed = cls._managed_roles(
            actor_role,
        )

        if allowed == MANAGES_ALL:
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
        target_role,
        *,
        room=None,
        location=None,
        department=None,
    ):
        if not actor_role or not target_role:
            return False

        if room:

            if not HierarchyService.can_assign_to_room(
                target_role,
            ):
                return False

            return ScopeService.can_access_room(
                actor_role,
                room,
            )

        if location:

            if not HierarchyService.can_assign_to_location(
                target_role,
            ):
                return False

            if actor_role.role == "SITE_ADMIN":
                return True

            if actor_role.department_id:
                return (
                    actor_role.department_id
                    == location.department_id
                )

            if actor_role.location_id:
                return (
                    actor_role.location_id
                    == location.id
                )

            return False

        if department:

            if not HierarchyService.can_assign_to_department(
                target_role,
            ):
                return False

            return (
                actor_role.role == "SITE_ADMIN"
                or actor_role.department_id == department.id
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
                target_role,
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
        if not actor_role or not assignment:
            return False

        return (
            cls.can_assign_role(
                actor_role,
                assignment.role,
            )
            and cls.can_assign_scope(
                actor_role,
                assignment.role,
                room=assignment.room,
                location=assignment.location,
                department=assignment.department,
            )
        )
    
    @classmethod
    def get_manageable_roles(
        cls,
        actor_role,
    ):
        """
        Return the set of role codes the actor may manage.

        May return MANAGES_ALL for unrestricted governance.
        """

        return cls._managed_roles(
            actor_role,
        )
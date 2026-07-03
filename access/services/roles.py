
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
    - Delegates object scope coverage to ScopeService.

    Does NOT determine:
    - Permission capability
    - General object visibility outside role governance
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

    @staticmethod
    def _scope_count(
        *,
        room=None,
        location=None,
        department=None,
    ):
        return sum(
            value is not None
            for value in [
                room,
                location,
                department,
            ]
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

        scope_count = RoleGovernanceService._scope_count(
            room=room,
            location=location,
            department=department,
        )

        # SITE_ADMIN role assignments are scope-less.
        if scope_count == 0:
            return (
                actor_role.role == "SITE_ADMIN"
                and HierarchyService.can_assign_to_site(
                    target_role,
                )
            )

        # All non-site role assignments must have exactly one scope.
        if scope_count > 1:
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

            actor_department_id = getattr(
                actor_role,
                "department_id",
                None,
            )
            actor_location_id = getattr(
                actor_role,
                "location_id",
                None,
            )

            if actor_department_id:
                return (
                    actor_department_id
                    == location.department_id
                )

            if actor_location_id:
                return (
                    actor_location_id
                    == location.id
                )

            return False

        if department:
            if not HierarchyService.can_assign_to_department(
                target_role,
            ):
                return False

            if actor_role.role == "SITE_ADMIN":
                return True

            return (
                getattr(
                    actor_role,
                    "department_id",
                    None,
                )
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

        return cls.can_assign(
            actor_role,
            assignment.role,
            room=assignment.room,
            location=assignment.location,
            department=assignment.department,
        )

    @classmethod
    def can_update_assignment(
        cls,
        actor_role,
        assignment,
        *,
        new_role=None,
        room=None,
        location=None,
        department=None,
    ):
        """
        Used for update flows.

        The actor must be allowed to manage the current assignment
        and must also be allowed to create/manage the intended new
        role/scope state.
        """
        if not cls.can_manage_assignment(
            actor_role,
            assignment,
        ):
            return False

        return cls.can_assign(
            actor_role,
            new_role or assignment.role,
            room=room if room is not None else assignment.room,
            location=(
                location
                if location is not None
                else assignment.location
            ),
            department=(
                department
                if department is not None
                else assignment.department
            ),
        )

    @classmethod
    def can_delete_assignment(
        cls,
        actor_role,
        assignment,
    ):
        return cls.can_manage_assignment(
            actor_role,
            assignment,
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
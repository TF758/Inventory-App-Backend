
from access.hierachy import DEPARTMENT, LOCATION, ROLE_HIERARCHY, ROOM, SITE
from users.models.roles import RoleAssignment


class HierarchyService:
    """
    Site hierarchy service.

    Determines which levels of the site hierarchy a
    role assignment may access and where roles may
    be assigned.

    Responsibilities
    ----------------
    - Navigation hierarchy
    - Role placement validation

    Does NOT determine:
    - Permissions (AccessService)
    - Object scope (ScopeService)
    - Business rules
    """

    # =====================================================
    # Internal Helpers
    # =====================================================

    @staticmethod
    def _config(
        role_assignment: RoleAssignment | None,
    ) -> dict:

        if not role_assignment:
            return {}

        return ROLE_HIERARCHY.get(
            role_assignment.role,
            {},
        )

    @classmethod
    def _has_access(
        cls,
        role_assignment: RoleAssignment | None,
        level: str,
    ) -> bool:

        return (
            level in cls._config(
                role_assignment,
            ).get(
                "access",
                set(),
            )
        )

    # =====================================================
    # Navigation
    # =====================================================

    @classmethod
    def can_access_site(
        cls,
        role_assignment: RoleAssignment | None,
    ) -> bool:

        return cls._has_access(
            role_assignment,
            SITE,
        )

    @classmethod
    def can_access_department(
        cls,
        role_assignment: RoleAssignment | None,
    ) -> bool:

        return cls._has_access(
            role_assignment,
            DEPARTMENT,
        )

    @classmethod
    def can_access_location(
        cls,
        role_assignment: RoleAssignment | None,
    ) -> bool:

        return cls._has_access(
            role_assignment,
            LOCATION,
        )

    @classmethod
    def can_access_room(
        cls,
        role_assignment: RoleAssignment | None,
    ) -> bool:

        return cls._has_access(
            role_assignment,
            ROOM,
        )

    # =====================================================
    # Assignment Validation
    # =====================================================

    @staticmethod
    def can_assign(
        role: str,
        level: str,
    ) -> bool:

        config = ROLE_HIERARCHY.get(
            role,
            {},
        )

        return (
            level in config.get(
                "assign",
                set(),
            )
        )

    @classmethod
    def can_assign_to_site(
        cls,
        role: str,
    ) -> bool:

        return cls.can_assign(
            role,
            SITE,
        )

    @classmethod
    def can_assign_to_department(
        cls,
        role: str,
    ) -> bool:

        return cls.can_assign(
            role,
            DEPARTMENT,
        )

    @classmethod
    def can_assign_to_location(
        cls,
        role: str,
    ) -> bool:

        return cls.can_assign(
            role,
            LOCATION,
        )

    @classmethod
    def can_assign_to_room(
        cls,
        role: str,
    ) -> bool:

        return cls.can_assign(
            role,
            ROOM,
        )
from users.models.roles import RoleAssignment
from sites.models.sites import Room
from sites.models.sites import UserPlacement


class ScopeService:

    # =====================================================
    # Core Scope Check
    # =====================================================

    @staticmethod
    def can_access_room(
        role_assignment: RoleAssignment,
        room: Room | None,
    ) -> bool:

        if not role_assignment:
            return False

        if not room:
            return False

        role = role_assignment.role

        # -------------------------
        # SITE
        # -------------------------

        if role == "SITE_ADMIN":
            return True

        # -------------------------
        # DEPARTMENT
        # -------------------------

        if role in {
            "DEPARTMENT_VIEWER",
            "DEPARTMENT_ADMIN",
        }:

            return (
                room.location
                and room.location.department_id
                == role_assignment.department_id
            )

        # -------------------------
        # LOCATION
        # -------------------------

        if role in {
            "LOCATION_VIEWER",
            "LOCATION_ADMIN",
        }:

            return (
                room.location_id
                == role_assignment.location_id
            )

        # -------------------------
        # ROOM
        # -------------------------

        if role in {
            "ROOM_VIEWER",
            "ROOM_CLERK",
            "ROOM_ADMIN",
        }:

            return (
                room.id
                == role_assignment.room_id
            )

        return False

    # =====================================================
    # Room Resolvers
    # =====================================================

    @staticmethod
    def get_asset_room(
        asset,
    ):
        return getattr(
            asset,
            "room",
            None,
        )

    @staticmethod
    def get_user_room(
        user,
    ):

        placement = (
            UserPlacement.objects
            .filter(
                user=user,
                is_current=True,
            )
            .select_related(
                "room",
                "room__location",
                "room__location__department",
            )
            .first()
        )

        if not placement:
            return None

        return placement.room

    @staticmethod
    def get_assignment_room(
        assignment,
    ):

        user = getattr(
            assignment,
            "user",
            None,
        )

        if not user:
            return None

        return ScopeService.get_user_room(
            user,
        )

    @staticmethod
    def get_return_request_room(
        request_item,
    ):
        return getattr(
            request_item,
            "room",
            None,
        )

    # =====================================================
    # Convenience Checks
    # =====================================================

    @staticmethod
    def can_access_asset( role_assignment, asset, ):
        """
        Resolve an asset to its room and evaluate
        access against the role hierarchy.

        Equipment, Consumables, Accessories and
        other asset types ultimately derive scope
        from a room.
        """

        room = ScopeService.get_asset_room(
            asset,
        )

        return ScopeService.can_access_room(
            role_assignment,
            room,
        )

    @staticmethod
    def can_access_user(
        role_assignment,
        user,
    ):

        room = ScopeService.get_user_room(
            user,
        )

        return ScopeService.can_access_room(
            role_assignment,
            room,
        )

    @staticmethod
    def can_access_assignment(
        role_assignment,
        assignment,
    ):

        room = ScopeService.get_assignment_room(
            assignment,
        )

        return ScopeService.can_access_room(
            role_assignment,
            room,
        )

    @staticmethod
    def can_access_return_request(
        role_assignment,
        request_item,
    ):

        room = ScopeService.get_return_request_room(
            request_item,
        )

        return ScopeService.can_access_room(
            role_assignment,
            room,
        )
    
class UserScopeService:

    @staticmethod
    def can_access_user(
        role_assignment: RoleAssignment,
        user,
    ) -> bool:

        if not role_assignment:
            return False

        if role_assignment.role == "SITE_ADMIN":
            return True

        # ---------------------------------
        # Current placement scope
        # ---------------------------------

        placements = (
            UserPlacement.objects
            .filter(
                user=user,
                is_current=True,
            )
            .select_related(
                "room",
                "room__location",
                "room__location__department",
            )
        )

        for placement in placements:

            if ScopeService.can_access_room(
                role_assignment,
                placement.room,
            ):
                return True

        # ---------------------------------
        # Role assignment scope
        # ---------------------------------

        roles = (
            RoleAssignment.objects
            .filter(user=user)
            .select_related(
                "room",
                "location",
                "department",
            )
        )

        for role in roles:

            if role.room:

                if ScopeService.can_access_room(
                    role_assignment,
                    role.room,
                ):
                    return True

            elif role.location:

                if (
                    role_assignment.role
                    == "SITE_ADMIN"
                ):
                    return True

                if (
                    role_assignment.location_id
                    == role.location_id
                ):
                    return True

                if (
                    role_assignment.department_id
                    and role.location.department_id
                    == role_assignment.department_id
                ):
                    return True

            elif role.department:

                if (
                    role_assignment.department_id
                    == role.department_id
                ):
                    return True

        return False
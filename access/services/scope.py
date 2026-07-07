from assignments.models.asset_assignment import ReturnRequest, ReturnRequestItem
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
            result = (
                room.location
                and room.location.department_id
                == role_assignment.department_id
            )
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
    def get_assignment_room( assignment, ):
        """
        Resolve the scope room for an assignment.

        Prefer the asset/equipment custody room when present.
        Fall back to the assigned user's current placement when
        the assignment object does not expose equipment directly.

        This fallback keeps generic assignment tests and lightweight
        assignment-like objects working.
        """

        if not assignment:
            return None

        room = getattr(
            assignment,
            "room",
            None,
        )

        if room:
            return room

        equipment = getattr(
            assignment,
            "equipment",
            None,
        )

        if equipment:
            equipment_room = getattr(
                equipment,
                "room",
                None,
            )

            if equipment_room:
                return equipment_room

        user = getattr(
            assignment,
            "user",
            None,
        )

        if user:
            return ScopeService.get_user_room(
                user,
            )

        return None
    
    @staticmethod
    def get_return_request_room(
        obj,
    ):
        if isinstance(obj, ReturnRequest):
            item = (
                obj.items
                .select_related("room")
                .first()
            )
            return item.room if item else None

        if isinstance(obj, ReturnRequestItem):
            return obj.room

        return None

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
    

    @staticmethod
    def can_access_role_assignment( role_assignment, assignment):
        """
        Determine whether a role assignment falls
        within the actor's scope.
        """

        if not role_assignment or not assignment:
            return False

        if assignment.room:
            return ScopeService.can_access_room(
                role_assignment,
                assignment.room,
            )

        if assignment.location:

            if role_assignment.role == "SITE_ADMIN":
                return True

            if role_assignment.department_id:
                return (
                    assignment.location.department_id
                    == role_assignment.department_id
                )

            if role_assignment.location_id:
                return (
                    assignment.location_id
                    == role_assignment.location_id
                )

            return False

        if assignment.department:

            if role_assignment.role == "SITE_ADMIN":
                return True

            return (
                role_assignment.department_id
                == assignment.department_id
            )

        # Site-level role assignment
        return (
            role_assignment.role
            == "SITE_ADMIN"
        )
    @staticmethod
    def _identity(obj):
        if not obj:
            return None

        return {
            "pk": getattr(obj, "pk", None),
            "id": getattr(obj, "id", None),
            "public_id": getattr(obj, "public_id", None),
            "name": getattr(obj, "name", None),
            "label": str(obj),
        }

    @staticmethod
    def check_access_assignment(
        role_assignment,
        assignment,
    ):
        """
        Debuggable assignment scope check.

        Returns a plain dict so PermissionDenied can safely serialize it.
        """

        if not role_assignment:
            return {
                "allowed": False,
                "reason": "NO_ACTIVE_ROLE",
                "assignment": ScopeService._identity(assignment),
            }

        if not assignment:
            return {
                "allowed": False,
                "reason": "NO_ASSIGNMENT",
                "active_role": {
                    "role": getattr(role_assignment, "role", None),
                    "public_id": getattr(role_assignment, "public_id", None),
                    "department": ScopeService._identity(
                        getattr(role_assignment, "department", None)
                    ),
                    "location": ScopeService._identity(
                        getattr(role_assignment, "location", None)
                    ),
                    "room": ScopeService._identity(
                        getattr(role_assignment, "room", None)
                    ),
                },
            }

        equipment = getattr(
            assignment,
            "equipment",
            None,
        )

        user = getattr(
            assignment,
            "user",
            None,
        )

        room = ScopeService.get_assignment_room(
            assignment,
        )

        location = (
            getattr(
                room,
                "location",
                None,
            )
            if room
            else None
        )

        department = (
            getattr(
                location,
                "department",
                None,
            )
            if location
            else None
        )

        if not room:
            return {
                "allowed": False,
                "reason": "ASSIGNMENT_HAS_NO_ROOM_SCOPE",
                "assignment": ScopeService._identity(assignment),
                "equipment": ScopeService._identity(equipment),
                "user": ScopeService._identity(user),
                "room": None,
                "location": None,
                "department": None,
                "active_role": {
                    "role": getattr(role_assignment, "role", None),
                    "public_id": getattr(role_assignment, "public_id", None),
                },
            }

        allowed = ScopeService.can_access_room(
            role_assignment,
            room,
        )

        return {
            "allowed": allowed,
            "reason": "IN_SCOPE" if allowed else "ROOM_OUT_OF_SCOPE",
            "assignment": ScopeService._identity(assignment),
            "equipment": ScopeService._identity(equipment),
            "user": ScopeService._identity(user),
            "room": ScopeService._identity(room),
            "location": ScopeService._identity(location),
            "department": ScopeService._identity(department),
            "active_role": {
                "role": getattr(role_assignment, "role", None),
                "public_id": getattr(role_assignment, "public_id", None),
                "department": ScopeService._identity(
                    getattr(role_assignment, "department", None)
                ),
                "location": ScopeService._identity(
                    getattr(role_assignment, "location", None)
                ),
                "room": ScopeService._identity(
                    getattr(role_assignment, "room", None)
                ),
            },
        }

    @staticmethod
    def can_access_assignment(
        role_assignment,
        assignment,
    ):
        """
        Boolean wrapper kept for existing callers.
        """

        check = ScopeService.check_access_assignment(
            role_assignment,
            assignment,
        )

        return check["allowed"]
    
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

   
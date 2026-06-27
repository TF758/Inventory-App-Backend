from access.permissions.scoped import ScopedPermission

from access.services.scope import ScopeService
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from access.services.hierachy import HierarchyService
from sites.models.sites import (
    Department,
    Location,
    Room,
)


class RoomPermission(ScopedPermission):

    permission_map = {
        "GET": "rooms.view",
        "POST": "rooms.create",
        "PUT": "rooms.update",
        "PATCH": "rooms.update",
        "DELETE": "rooms.delete",
    }

    def has_permission(
        self,
        request,
        view,
    ):
        if not super().has_permission(
            request,
            view,
        ):
            return False

        # ---------------------------------
        # Creation validation
        # ---------------------------------

        if request.method == "POST":

            location_id = request.data.get(
                "location",
            )

            if not location_id:
                return False

            location = Location.objects.filter(
                public_id=location_id,
            ).first()

            if not location:
                return False

            active_role = getattr(
                request.user,
                "active_role",
                None,
            )

            if not active_role:
                return False

            if not HierarchyService.can_access_room(
                active_role,
            ):
                return False

            if active_role.role == "SITE_ADMIN":
                return True

            if active_role.department_id:
                return (
                    active_role.department_id
                    == location.department_id
                )

            if active_role.location_id:
                return (
                    active_role.location_id
                    == location.id
                )

            return False

        return True

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        # ---------------------------------
        # Business rule
        # Only department/site admins may
        # move a room.
        # ---------------------------------

        if (
            request.method in ["PUT", "PATCH"]
            and "location" in request.data
        ):
            return (
                active_role.role in {
                    "DEPARTMENT_ADMIN",
                    "SITE_ADMIN",
                }
            )

        return (
            HierarchyService.can_access_room(
                active_role,
            )
            and ScopeService.can_access_room(
                active_role,
                obj,
            )
        )

class RoomContextPermission(BasePermission):
    """
    Validates access to the Room context.

    Responsible only for:

    - hierarchy validation
    - room scope validation

    Does NOT check capabilities.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        if not HierarchyService.can_access_room(
            active_role,
        ):
            return False

        public_id = view.kwargs.get("public_id")

        if not public_id:
            return True

        room = get_object_or_404(
            Room,
            public_id=public_id,
        )

        if active_role.role == "SITE_ADMIN":
            return True

        return ScopeService.can_access_room(
            active_role,
            room,
        )
    
class LocationPermission(ScopedPermission):

    permission_map = {
        "GET": "locations.view",
        "POST": "locations.create",
        "PUT": "locations.update",
        "PATCH": "locations.update",
        "DELETE": "locations.delete",
    }

    def has_permission(
        self,
        request,
        view,
    ):
        if not super().has_permission(
            request,
            view,
        ):
            return False

        # ---------------------------------
        # Creation validation
        # ---------------------------------

        if request.method == "POST":

            department_id = request.data.get(
                "department",
            )

            if not department_id:
                return False

            department = Department.objects.filter(
                public_id=department_id,
            ).first()

            if not department:
                return False

            active_role = getattr(
                request.user,
                "active_role",
                None,
            )

            if not active_role:
                return False

            if not HierarchyService.can_access_location(
                active_role,
            ):
                return False

            if active_role.role == "SITE_ADMIN":
                return True

            return (
                active_role.department_id
                == department.id
            )

        return True

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        # ---------------------------------
        # Business rule
        # Only SITE_ADMIN may move a
        # location between departments.
        # ---------------------------------

        if (
            request.method in ["PUT", "PATCH"]
            and "department" in request.data
        ):
            return (
                active_role.role
                == "SITE_ADMIN"
            )

        return (
            HierarchyService.can_access_location(
                active_role,
            )
            and (
                active_role.role == "SITE_ADMIN"
                or active_role.department_id
                == obj.department_id
            )
        )

class LocationContextPermission(BasePermission):
    """
    Validates access to the Location context.

    Responsible only for:

    - hierarchy validation
    - location scope validation

    Does NOT check capabilities.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        if not HierarchyService.can_access_location(
            active_role,
        ):
            return False

        public_id = view.kwargs.get("public_id")

        if not public_id:
            return True

        location = get_object_or_404(
            Location,
            public_id=public_id,
        )

        if active_role.role == "SITE_ADMIN":
            return True

        if active_role.department_id:
            return (
                active_role.department_id
                == location.department_id
            )

        if active_role.location_id:
            return (
                active_role.location_id
                == location.id
            )

        return False

class DepartmentPermission(ScopedPermission):

    permission_map = {
        "GET": "departments.view",
        "POST": "departments.create",
        "PUT": "departments.update",
        "PATCH": "departments.update",
        "DELETE": "departments.delete",
    }

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        # ---------------------------------
        # Business rule
        # Only SITE_ADMIN may rename a
        # department.
        # ---------------------------------

        if (
            request.method in ["PUT", "PATCH"]
            and "name" in request.data
        ):
            return (
                active_role.role
                == "SITE_ADMIN"
            )

        return (
            HierarchyService.can_access_department(
                active_role,
            )
            and (
                active_role.role == "SITE_ADMIN"
                or active_role.department_id
                == obj.id
            )
        )
    

class DepartmentContextPermission(BasePermission):
    """
    Validates access to the Department context.

    Responsible only for:

    - hierarchy validation
    - department scope validation

    Does NOT check capabilities.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        if not HierarchyService.can_access_department(
            active_role,
        ):
            return False

        public_id = view.kwargs.get("public_id")

        if not public_id:
            return True

        department = get_object_or_404(
            Department,
            public_id=public_id,
        )

        if active_role.role == "SITE_ADMIN":
            return True

        return (
            active_role.department_id
            == department.id
        )
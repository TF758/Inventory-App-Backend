from access.permissions.scoped import ScopedPermission
from rest_framework.exceptions import PermissionDenied
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

    def _deny(
        self,
        reason,
        *,
        active_role=None,
        obj=None,
        method=None,
        view=None,
        extra=None,
    ):
        detail = {
            "detail": "Location permission denied.",
            "reason": reason,
            "active_role": getattr(active_role, "role", None),
            "active_role_public_id": getattr(active_role, "public_id", None),
            "active_department_id": getattr(active_role, "department_id", None),
            "active_location_id": getattr(active_role, "location_id", None),
            "active_room_id": getattr(active_role, "room_id", None),
            "object_id": getattr(obj, "id", None),
            "object_public_id": getattr(obj, "public_id", None),
            "object_department_id": getattr(obj, "department_id", None),
            "method": method,
            "view": view.__class__.__name__ if view else None,
            "action": getattr(view, "action", None),
        }

        if extra:
            detail.update(extra)

        raise PermissionDenied(detail)

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

        if not super().has_permission(
            request,
            view,
        ):
            self._deny(
                "MISSING_LOCATION_PERMISSION_CODE",
                active_role=active_role,
                method=request.method,
                view=view,
                extra={
                    "required_permission": self.permission_map.get(
                        request.method,
                    ),
                },
            )

        # ---------------------------------
        # Creation validation
        # ---------------------------------

        if request.method == "POST":

            department_id = request.data.get(
                "department",
            )

            if not department_id:
                self._deny(
                    "MISSING_DEPARTMENT_FOR_LOCATION_CREATE",
                    active_role=active_role,
                    method=request.method,
                    view=view,
                )

            department = Department.objects.filter(
                public_id=department_id,
            ).first()

            if not department:
                self._deny(
                    "TARGET_DEPARTMENT_NOT_FOUND",
                    active_role=active_role,
                    method=request.method,
                    view=view,
                    extra={
                        "submitted_department": department_id,
                    },
                )

            if not active_role:
                self._deny(
                    "NO_ACTIVE_ROLE",
                    method=request.method,
                    view=view,
                )

            if not HierarchyService.can_access_location(
                active_role,
            ):
                self._deny(
                    "ROLE_CANNOT_ACCESS_LOCATION_LEVEL",
                    active_role=active_role,
                    method=request.method,
                    view=view,
                )

            if active_role.role == "SITE_ADMIN":
                return True

            if active_role.department_id == department.id:
                return True

            self._deny(
                "CREATE_LOCATION_OUTSIDE_ACTIVE_ROLE_SCOPE",
                active_role=active_role,
                method=request.method,
                view=view,
                extra={
                    "target_department_id": department.id,
                    "target_department_public_id": department.public_id,
                },
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
            self._deny(
                "NO_ACTIVE_ROLE",
                obj=obj,
                method=request.method,
                view=view,
            )

        # ---------------------------------
        # Business rule
        # Only SITE_ADMIN may move a
        # location between departments.
        # ---------------------------------

        if (
            request.method in ["PUT", "PATCH"]
            and "department" in request.data
        ):
            if active_role.role == "SITE_ADMIN":
                return True

            self._deny(
                "ONLY_SITE_ADMIN_CAN_TRANSFER_LOCATION",
                active_role=active_role,
                obj=obj,
                method=request.method,
                view=view,
            )

        if not HierarchyService.can_access_location(
            active_role,
        ):
            self._deny(
                "ROLE_CANNOT_ACCESS_LOCATION_LEVEL",
                active_role=active_role,
                obj=obj,
                method=request.method,
                view=view,
            )

        if active_role.role == "SITE_ADMIN":
            return True

        # Department-scoped role can access locations in its department.
        if (
            active_role.department_id
            and active_role.department_id == obj.department_id
        ):
            return True

        # Location-scoped role can access its exact location.
        if (
            active_role.location_id
            and active_role.location_id == obj.id
        ):
            return True

        self._deny(
            "LOCATION_OUTSIDE_ACTIVE_ROLE_SCOPE",
            active_role=active_role,
            obj=obj,
            method=request.method,
            view=view,
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
from rest_framework.permissions import BasePermission

from core.permissions.constants import ROLE_HIERARCHY
from core.permissions.helpers import has_hierarchy_permission, is_admin_role, is_in_scope, is_viewer_role
from access.permissions.scoped import ScopedPermission
from access.services.scope import ScopeService
from sites.models.sites import Department, Location, Room



class RoomPermission( ScopedPermission, ):

    permission_map = {
        "GET": "rooms.view",
        "POST": "rooms.create",
        "PUT": "rooms.update",
        "PATCH": "rooms.update",
        "DELETE": "rooms.delete",
    }

    def has_permission( self, request, view, ):
        if not super().has_permission(
            request,
            view,
        ):
            return False

        # creation scope validation

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

            if active_role.role == "SITE_ADMIN":
                return True

            if active_role.role in {
                "DEPARTMENT_ADMIN",
                "LOCATION_ADMIN",
            }:

                if active_role.role == "LOCATION_ADMIN":
                    return (
                        active_role.location_id
                        == location.id
                    )

                return (
                    active_role.department_id
                    == location.department_id
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

        # business rule:
        # only department/site admins may
        # move a room to another location

        if (
            request.method in ["PUT", "PATCH"]
            and "location" in request.data
        ):
            return (
                active_role.role
                in {
                    "DEPARTMENT_ADMIN",
                    "SITE_ADMIN",
                }
            )

        if active_role.role == "SITE_ADMIN":
            return True

        return ScopeService.can_access_room(
            active_role,
            obj,
        )
    
class LocationPermission( ScopedPermission):

    permission_map = {
        "GET": "locations.view",
        "POST": "locations.create",
        "PUT": "locations.update",
        "PATCH": "locations.update",
        "DELETE": "locations.delete",
    }

    def has_permission( self, request, view, ):
        if not super().has_permission(
            request,
            view,
        ):
            return False

        # creation scope validation

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

            if active_role.role == "SITE_ADMIN":
                return True

            return (
                active_role.department_id
                == department.id
            )

        return True

    def has_object_permission( self, request, view, obj, ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        # business rule:
        # only SITE_ADMIN may move a location
        # to another department

        if (
            request.method in ["PUT", "PATCH"]
            and "department" in request.data
        ):
            return (
                active_role.role
                == "SITE_ADMIN"
            )

        if active_role.role == "SITE_ADMIN":
            return True

        return (
            active_role.department_id
            == obj.department_id
        )
    
class DepartmentPermission( ScopedPermission, ):

    permission_map = {
        "GET": "departments.view",
        "POST": "departments.create",
        "PUT": "departments.update",
        "PATCH": "departments.update",
        "DELETE": "departments.delete",
    }

    def has_object_permission( self, request, view, obj, ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        # Business rule:
        # only SITE_ADMIN may rename departments

        if (
            request.method in ["PUT", "PATCH"]
            and "name" in request.data
        ):
            return (
                active_role.role
                == "SITE_ADMIN"
            )

        if active_role.role == "SITE_ADMIN":
            return True

        return (
            active_role.department_id
            == obj.id
        )
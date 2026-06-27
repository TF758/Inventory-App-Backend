from access.permissions.scoped import (
    ScopedPermission,
)


from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)

from access.services.access import AccessService
from core.permissions.helpers import is_in_scope
from inventory.access.services.scope import ScopeService



# class AssetPermission(
#     ScopedPermission
# ):

#     permission_map = {
#         "GET": "assets.view",
#         "POST": "assets.create",
#         "PUT": "assets.update",
#         "PATCH": "assets.update",
#         "DELETE": "assets.delete",
#     }

#     def has_object_permission(
#         self,
#         request,
#         view,
#         obj,
#     ):
#         active_role = getattr(
#             request.user,
#             "active_role",
#             None,
#         )

#         if not active_role:
#             return False

#         permission_code = self.get_required_permission(
#             request,
#             view,
#         )

#         if not permission_code:
#             return False

#         room_for_scope = getattr(
#             obj,
#             "room",
#             None,
#         )

#         if (
#             hasattr(obj, "equipment")
#             and obj.equipment
#         ):
#             room_for_scope = obj.equipment.room

#         return (
#             self.has_permission(
#                 request,
#                 view,
#             )
#             and is_in_scope(
#                 active_role,
#                 room=room_for_scope,
#             )
#         )


class AssetPermission(
    ScopedPermission,
):
    """
    Asset authorization.

    Permission checks are handled by AccessService
    through ScopedPermission.

    Object-level scope checks are delegated to
    ScopeService so users can only interact with
    assets that fall within their assigned
    department/location/room hierarchy.
    """

    permission_map = {
        "GET": "assets.view",
        "POST": "assets.create",
        "PUT": "assets.update",
        "PATCH": "assets.update",
        "DELETE": "assets.delete",
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

        return (
            self.has_permission(
                request,
                view,
            )
            and ScopeService.can_access_asset(
                active_role,
                obj,
            )
        )
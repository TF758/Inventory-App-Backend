from django.db.models import Q
from django.contrib.auth import get_user_model
from assets.models.assets import Accessory, AssetAgreement, AssetAgreementItem, Component, Consumable, Equipment
from assignments.models.asset_assignment import ReturnRequest
from core.models.audit import AuditLog
from core.utils.scope.base import BaseScopePolicy
from sites.models.sites import Department, Location, Room, UserPlacement

from users.models.roles import RoleAssignment

POLICY_REGISTRY = {}


def register(model):
    """
    Register a scope policy class for a model.

    The registry lets the scope service dispatch to the correct policy
    without maintaining a large if/elif chain.
    """
    def wrapper(policy_cls):
        POLICY_REGISTRY[model] = policy_cls
        return policy_cls

    return wrapper


@register(Room)
class RoomScopePolicy(BaseScopePolicy):
    """
    Scope rooms by the user's active room/location/department.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if self.scope.level == "room":
            return self.queryset.filter(pk=self.scope.obj.pk)

        if self.scope.level == "location":
            return self.queryset.filter(location=self.scope.obj)

        if self.scope.level == "department":
            return self.queryset.filter(location__department=self.scope.obj)

        return self.queryset.none()


@register(Location)
class LocationScopePolicy(BaseScopePolicy):
    """
    Scope locations.

    Room-level roles cannot see locations.
    Location-level roles see their location.
    Department-level roles see locations in their department.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if self.scope.level == "room":
            return self.queryset.none()

        if self.scope.level == "location":
            return self.queryset.filter(pk=self.scope.obj.pk)

        if self.scope.level == "department":
            return self.queryset.filter(department=self.scope.obj)

        return self.queryset.none()


@register(Department)
class DepartmentScopePolicy(BaseScopePolicy):
    """
    Scope departments.

    Only department-level roles can see their department.
    Room/location-level roles cannot see department rows.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if self.scope.level in {"room", "location"}:
            return self.queryset.none()

        if self.scope.level == "department":
            return self.queryset.filter(pk=self.scope.obj.pk)

        return self.queryset.none()


@register(AuditLog)
class AuditLogScopePolicy(BaseScopePolicy):
    """
    Scope audit logs by room/location/department fields.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        return self.queryset.filter(self.room_hierarchy_q()).distinct()


@register(Equipment)
class EquipmentScopePolicy(BaseScopePolicy):
    """
    Scope equipment by hierarchy, plus include equipment actively assigned to user.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        scope_q = self.room_hierarchy_q()

        assignment_q = Q(
            active_assignment__user=self.user,
            active_assignment__returned_at__isnull=True,
        )

        return self.queryset.filter(scope_q | assignment_q).distinct()


@register(Accessory)
class AccessoryScopePolicy(BaseScopePolicy):
    """
    Scope accessories by hierarchy, plus include accessories assigned to user.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        scope_q = self.room_hierarchy_q()

        assignment_q = Q(
            assignments__user=self.user,
            assignments__returned_at__isnull=True,
            assignments__quantity__gt=0,
        )

        return self.queryset.filter(scope_q | assignment_q).distinct()


@register(Consumable)
class ConsumableScopePolicy(BaseScopePolicy):
    """
    Scope consumables by hierarchy, plus include issued consumables assigned to user.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        scope_q = self.room_hierarchy_q()

        assignment_q = Q(
            issues__user=self.user,
            issues__returned_at__isnull=True,
            issues__quantity__gt=0,
        )

        return self.queryset.filter(scope_q | assignment_q).distinct()


@register(Component)
class ComponentScopePolicy(BaseScopePolicy):
    """
    Scope components through their parent equipment.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        if self.scope.level == "room":
            q = Q(equipment__room=self.scope.obj)

        elif self.scope.level == "location":
            q = Q(equipment__room__location=self.scope.obj)

        elif self.scope.level == "department":
            q = Q(equipment__room__location__department=self.scope.obj)

        else:
            return self.queryset.none()

        return self.queryset.filter(q).distinct()



@register(RoleAssignment)
class RoleAssignmentScopePolicy(BaseScopePolicy):
    """
    Scope role assignments by room/location/department hierarchy.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        role = self.role

        if role.room:
            return self.queryset.filter(room=role.room).distinct()

        if role.location:
            return self.queryset.filter(
                Q(location=role.location) |
                Q(room__location=role.location)
            ).distinct()

        if role.department:
            return self.queryset.filter(
                Q(department=role.department)
                | Q(location__department=role.department)
                | Q(room__location__department=role.department)
            ).distinct()

        return self.queryset.none()


@register(AssetAgreement)
class AssetAgreementScopePolicy(BaseScopePolicy):

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        role = self.role

        if role.room:
            return self.queryset.filter(room=role.room).distinct()

        if role.location:
            return self.queryset.filter(
                Q(location=role.location) |
                Q(room__location=role.location)
            ).distinct()

        if role.department:
            return self.queryset.filter(
                Q(department=role.department)
                | Q(location__department=role.department)
                | Q(room__location__department=role.department)
            ).distinct()

        return self.queryset.none()

@register(ReturnRequest)
class ReturnRequestScopePolicy(BaseScopePolicy):
    """
    Scope return requests through the requester's current placement.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        if self.scope.level == "room":
            q = Q(
                requester__user_placements__is_current=True,
                requester__user_placements__room=self.scope.obj,
            )

        elif self.scope.level == "location":
            q = Q(
                requester__user_placements__is_current=True,
                requester__user_placements__room__location=self.scope.obj,
            )

        elif self.scope.level == "department":
            q = Q(
                requester__user_placements__is_current=True,
                requester__user_placements__room__location__department=self.scope.obj,
            )

        else:
            return self.queryset.none()

        return self.queryset.filter(q).distinct()


@register(AssetAgreementItem)
class AssetAgreementItemScopePolicy(BaseScopePolicy):
    """
    Scope agreement items through their parent agreement.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        if self.scope.level == "room":
            q = Q(agreement__room=self.scope.obj)

        elif self.scope.level == "location":
            q = Q(agreement__location=self.scope.obj)

        elif self.scope.level == "department":
            q = Q(agreement__department=self.scope.obj)

        else:
            return self.queryset.none()

        return self.queryset.filter(q).distinct()


@register(UserPlacement)
class UserPlacementScopePolicy(BaseScopePolicy):
    """
    Scope user placements by placement room hierarchy.

    NOTE:
        This intentionally preserves the original priority:
        department > location > room.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if self.role.department:
            return self.queryset.filter(
                room__location__department=self.role.department
            ).distinct()

        if self.role.location:
            return self.queryset.filter(
                room__location=self.role.location
            ).distinct()

        if self.role.room:
            return self.queryset.filter(
                room=self.role.room
            ).distinct()

        return self.queryset.none()


@register(get_user_model())
class UserScopePolicy(BaseScopePolicy):
    """
    Scope users by role assignments and current placements.

    Also preserves the original admin-created-user visibility rule.
    """

    def apply(self):
        if self.scope.is_site_admin():
            return self.queryset

        if not self.scope.level:
            return self.queryset.none()

        q = Q()

        if self.scope.level == "department":
            q |= Q(role_assignments__department=self.scope.obj)
            q |= Q(user_placements__room__location__department=self.scope.obj)

        elif self.scope.level == "location":
            q |= Q(role_assignments__location=self.scope.obj)
            q |= Q(user_placements__room__location=self.scope.obj)

        elif self.scope.level == "room":
            q |= Q(role_assignments__room=self.scope.obj)
            q |= Q(user_placements__room=self.scope.obj)

        if self.role.role in ["DEPARTMENT_ADMIN", "LOCATION_ADMIN", "ROOM_ADMIN"]:
            q |= Q(
                active_role__isnull=True,
                created_by__role_assignments__department=self.role.department,
            )

        return self.queryset.filter(q).distinct()

"""Department, location, and room dashboard aggregation."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from assignments.models.asset_assignment import EquipmentAssignment, ReturnRequest
from assets.models.assets import (
    Accessory,
    Component,
    Consumable,
    Equipment,
    EquipmentStatus,
)
from users.models.roles import RoleAssignment


class AreaDashboardMixin:
    """Build a shared dashboard for department, location, or room objects."""

    ADMIN_ROLES = (
        "SITE_ADMIN",
        "DEPARTMENT_ADMIN",
        "LOCATION_ADMIN",
        "ROOM_ADMIN",
    )
    OVERDUE_RETURN_DAYS = 7

    def get_rooms(self, public_id):
        raise NotImplementedError

    @staticmethod
    def _role_scope_query(obj):
        if hasattr(obj, "locations"):
            return (
                Q(department=obj)
                | Q(location__department=obj)
                | Q(room__location__department=obj)
            )

        if hasattr(obj, "rooms"):
            return Q(location=obj) | Q(room__location=obj)

        return Q(room=obj)

    def build_dashboard(self, obj):
        rooms = self.get_rooms(obj.public_id)

        equipment = Equipment.objects.filter(
            room__in=rooms,
            is_deleted=False,
        )
        total_equipment = equipment.count()

        assigned_equipment = EquipmentAssignment.objects.filter(
            equipment__room__in=rooms,
            equipment__is_deleted=False,
            returned_at__isnull=True,
        ).count()

        utilization = round(
            assigned_equipment / total_equipment * 100
            if total_equipment
            else 0,
            1,
        )

        damaged_equipment = equipment.filter(
            status__in=(
                EquipmentStatus.DAMAGED,
                EquipmentStatus.UNDER_REPAIR,
            )
        ).count()
        lost_or_condemned = equipment.filter(
            status__in=(
                EquipmentStatus.LOST,
                EquipmentStatus.CONDEMNED,
            )
        ).count()

        consumables = Consumable.objects.filter(
            room__in=rooms,
            is_deleted=False,
        )
        low_stock = consumables.filter(
            quantity__gt=0,
            quantity__lte=F("low_stock_threshold"),
        ).count()
        out_of_stock = consumables.filter(quantity=0).count()

        accessories = Accessory.objects.filter(
            room__in=rooms,
            is_deleted=False,
        )
        components = Component.objects.filter(equipment__room__in=rooms)

        roles = RoleAssignment.objects.filter(self._role_scope_query(obj))
        total_users = roles.values("user").distinct().count()
        admin_users = (
            roles.filter(role__in=self.ADMIN_ROLES)
            .values("user")
            .distinct()
            .count()
        )

        return_requests = ReturnRequest.objects.filter(
            requester__user_placements__is_current=True,
            requester__user_placements__room__in=rooms,
        ).distinct()
        pending_requests = return_requests.filter(
            status=ReturnRequest.Status.PENDING
        ).count()
        overdue_requests = return_requests.filter(
            status=ReturnRequest.Status.PENDING,
            requested_at__lte=(
                timezone.now() - timedelta(days=self.OVERDUE_RETURN_DAYS)
            ),
        ).count()

        return {
            "summary": {
                "assets": {
                    "equipment": total_equipment,
                    "accessories": accessories.count(),
                    "components": components.count(),
                    "consumables": consumables.count(),
                },
                "equipment_utilization": {
                    "assigned": assigned_equipment,
                    "total": total_equipment,
                    "percent": utilization,
                },
                "stock_risk": {
                    "low_stock_consumables": low_stock,
                    "out_of_stock_consumables": out_of_stock,
                },
                "equipment_issues": {
                    "damaged": damaged_equipment,
                    "lost_or_condemned": lost_or_condemned,
                },
                "users": {
                    "total": total_users,
                    "admins": admin_users,
                    "non_admins": max(total_users - admin_users, 0),
                },
                "returns": {
                    "pending": pending_requests,
                    "overdue": overdue_requests,
                },
            },
            "attention": {
                "damaged_equipment": damaged_equipment,
                "out_of_stock_consumables": out_of_stock,
                "low_stock_consumables": low_stock,
                "pending_returns": pending_requests,
                "overdue_returns": overdue_requests,
            },
        }

"""Accessory dashboard aggregation."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from assignments.models.asset_assignment import AccessoryAssignment, AccessoryEvent
from assets.models.assets import Accessory

from .base import PeriodDashboardMixin


class AccessoryDashboardMixin(PeriodDashboardMixin):
    """Build accessory inventory and recent-event dashboard data."""

    EVENT_TYPES = (
        "assigned",
        "returned",
        "used",
        "lost",
        "damaged",
        "condemned",
        "restocked",
        "adjusted",
    )

    def build_dashboard_response(self, rooms, period):
        since = timezone.now() - timedelta(days=period)

        accessories = Accessory.objects.filter(
            room__in=rooms,
            is_deleted=False,
        )
        summary = accessories.aggregate(
            accessory_types=Count("id"),
            total_quantity=Sum("quantity"),
        )
        total_quantity = summary["total_quantity"] or 0

        active_assignments = AccessoryAssignment.objects.filter(
            accessory__room__in=rooms,
            accessory__is_deleted=False,
            returned_at__isnull=True,
        )
        assigned_quantity = (
            active_assignments.aggregate(total=Sum("quantity"))["total"] or 0
        )

        event_rows = (
            AccessoryEvent.objects.filter(
                accessory__room__in=rooms,
                accessory__is_deleted=False,
                occurred_at__gte=since,
            )
            .values("event_type")
            .annotate(count=Count("id"))
        )
        event_counts = {
            row["event_type"]: row["count"]
            for row in event_rows
        }

        return {
            "summary": {
                "accessory_types": summary["accessory_types"],
                "total_quantity": total_quantity,
                "assigned_quantity": assigned_quantity,
                "unassigned_quantity": max(
                    total_quantity - assigned_quantity,
                    0,
                ),
                "active_assignments": active_assignments.count(),
            },
            "events": {
                event_type: event_counts.get(event_type, 0)
                for event_type in self.EVENT_TYPES
            },
            "meta": {"period_days": period},
        }

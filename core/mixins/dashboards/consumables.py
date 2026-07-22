"""Consumable dashboard aggregation."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, F, Sum
from django.utils import timezone

from assignments.models.asset_assignment import ConsumableEvent
from assets.models.assets import Consumable

from .base import PeriodDashboardMixin


class ConsumableDashboardMixin(PeriodDashboardMixin):
    """Build consumable stock-health and recent-movement dashboard data."""

    EVENT_TYPES = (
        "issued",
        "used",
        "returned",
        "lost",
        "damaged",
        "expired",
        "condemned",
        "restocked",
        "adjusted",
    )

    def build_dashboard_response(self, rooms, period):
        since = timezone.now() - timedelta(days=period)

        consumables = Consumable.objects.filter(
            room__in=rooms,
            is_deleted=False,
        )
        summary = consumables.aggregate(
            consumable_types=Count("id"),
            total_quantity=Sum("quantity"),
        )
        total_quantity = summary["total_quantity"] or 0

        low_stock_count = consumables.filter(
            quantity__lte=F("low_stock_threshold")
        ).count()
        out_of_stock_count = consumables.filter(quantity=0).count()

        event_rows = (
            ConsumableEvent.objects.filter(
                consumable__room__in=rooms,
                consumable__is_deleted=False,
                occurred_at__gte=since,
            )
            .values("event_type")
            .annotate(quantity=Sum("quantity_change"))
        )
        event_quantities = {
            row["event_type"]: abs(row["quantity"] or 0)
            for row in event_rows
        }

        return {
            "summary": {
                "consumable_types": summary["consumable_types"],
                "total_quantity": total_quantity,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "issued_quantity": event_quantities.get("issued", 0),
            },
            "events": {
                event_type: event_quantities.get(event_type, 0)
                for event_type in self.EVENT_TYPES
            },
            "meta": {"period_days": period},
        }

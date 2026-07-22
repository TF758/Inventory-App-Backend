"""Dashboard-specific mixins."""

from .accessories import AccessoryDashboardMixin
from .areas import AreaDashboardMixin
from .consumables import ConsumableDashboardMixin

__all__ = [
    "AccessoryDashboardMixin",
    "AreaDashboardMixin",
    "ConsumableDashboardMixin",
]

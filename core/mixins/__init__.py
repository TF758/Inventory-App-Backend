"""Reusable view mixins, grouped by responsibility.

This package intentionally re-exports the original public API so existing
imports such as ``from core.mixins import AuditMixin`` continue to work after
replacing the former ``core/mixins.py`` module with this package.
"""

from .access import RoleVisibilityMixin, ScopeFilterMixin
from .audit import AuditMixin
from .caching import (
    SiteOptionInvalidationMixin,
    UserScopeListCacheMixin,
)
from .dashboards import (
    AccessoryDashboardMixin,
    AreaDashboardMixin,
    ConsumableDashboardMixin,
)
from .filters import ExcludeFiltersMixin
from .notifications import NotificationMixin
from .serializers import ListDetailSerializerMixin
from .viewsets import LightEndpointMixin

__all__ = [
    "AccessoryDashboardMixin",
    "AreaDashboardMixin",
    "AuditMixin",
    "ConsumableDashboardMixin",
    "ExcludeFiltersMixin",
    "LightEndpointMixin",
    "ListDetailSerializerMixin",
    "NotificationMixin",
    "RoleVisibilityMixin",
    "ScopeFilterMixin",
    "SiteOptionInvalidationMixin",
    "UserScopeListCacheMixin",
]
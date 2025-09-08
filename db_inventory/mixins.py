from rest_framework import viewsets
from .permissions import filter_queryset_by_scope
from rest_framework.exceptions import PermissionDenied
from .models import Location, Department

class ScopeFilterMixin:
    """
    Mixin to automatically filter a queryset based on the user's *active role*.
    Assumes the viewset has either:
      - a `model_class` attribute, OR
      - a `queryset` defined (from which model_class can be inferred).
    """

    model_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        model_class = self.model_class or queryset.model
        active_role = getattr(self.request.user, "active_role", None)

        if not active_role:
            return queryset.none()

        if active_role.role == "SITE_ADMIN":
            return queryset
        
        if model_class in [Location, Department] and active_role.room:
            raise PermissionDenied("Room-level roles cannot access this endpoint.")
        
        if model_class in [Department] and active_role.location:
            raise PermissionDenied("Location-level roles cannot access this endpoint.")

        # Only filter for list action
        if self.action == "list":
            return filter_queryset_by_scope(self.request.user, queryset, model_class)

        return queryset
"""Queryset scope and role-visibility mixins."""

from __future__ import annotations

from ..permissions import filter_queryset_by_scope


class ScopeFilterMixin:
    """Filter a queryset using the requesting user's active role and scope."""

    model_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        model_class = self.model_class or queryset.model
        active_role = getattr(self.request.user, "active_role", None)

        if not active_role:
            return queryset.none()

        if active_role.role == "SITE_ADMIN":
            return queryset

        return filter_queryset_by_scope(
            self.request.user,
            queryset,
            model_class,
        )


class RoleVisibilityMixin:
    """Filter role assignments that the requesting user's active role may see."""

    def filter_visibility(self, queryset):
        active_role = getattr(self.request.user, "active_role", None)

        if not active_role:
            return queryset.none()

        if active_role.role == "SITE_ADMIN":
            return queryset

        if active_role.role == "DEPARTMENT_ADMIN":
            return queryset.exclude(role="DEPARTMENT_ADMIN")

        if active_role.role == "LOCATION_ADMIN":
            return queryset.exclude(
                role__in=[
                    "DEPARTMENT_ADMIN",
                    "DEPARTMENT_VIEWER",
                    "LOCATION_ADMIN",
                ]
            )

        if active_role.role == "ROOM_ADMIN":
            return queryset.filter(role__in=["ROOM_CLERK", "ROOM_VIEWER"])

        return queryset.none()

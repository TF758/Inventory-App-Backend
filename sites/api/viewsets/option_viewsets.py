# sites/api/option_viewsets.py

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated


from core.mixins import ScopeFilterMixin
from core.pagination import FlexiblePagination
from core.mixins.caching.user_scope_list_cache import UserScopeListCacheMixin
from sites.api.serializers.option_serializers import (
    DepartmentOptionSerializer,
    LocationOptionSerializer,
    RoomOptionSerializer,
)
from sites.models.sites import Department, Location, Room


class DepartmentOptionViewSet( UserScopeListCacheMixin, ScopeFilterMixin, mixins.ListModelMixin, viewsets.GenericViewSet, ):
    scope_cache_namespace = "department-options"

    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentOptionSerializer
    pagination_class = FlexiblePagination
    queryset = Department.objects.all().order_by("name")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]


class LocationOptionViewSet( UserScopeListCacheMixin, ScopeFilterMixin, mixins.ListModelMixin, viewsets.GenericViewSet, ):
    scope_cache_namespace = "location-options"

    permission_classes = [IsAuthenticated]
    serializer_class = LocationOptionSerializer
    pagination_class = FlexiblePagination
    queryset = (
        Location.objects.select_related("department")
        .all()
        .order_by("name")
    )
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name", "department__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get("department_id")

        if department_id:
            queryset = queryset.filter(
                department__public_id=department_id,
            )

        return queryset


class RoomOptionViewSet( UserScopeListCacheMixin, ScopeFilterMixin, mixins.ListModelMixin, viewsets.GenericViewSet, ):
    scope_cache_namespace = "room-options"

    permission_classes = [IsAuthenticated]
    serializer_class = RoomOptionSerializer
    pagination_class = FlexiblePagination
    queryset = (
        Room.objects.select_related(
            "location",
            "location__department",
        )
        .all()
        .order_by("name")
    )
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = [
        "name",
        "location__name",
        "location__department__name",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get("department_id")
        location_id = self.request.query_params.get("location_id")

        if department_id:
            queryset = queryset.filter(
                location__department__public_id=department_id,
            )

        if location_id:
            queryset = queryset.filter(
                location__public_id=location_id,
            )

        return queryset

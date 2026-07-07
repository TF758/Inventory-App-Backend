# sites/api/option_viewsets.py

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from core.mixins import ScopeFilterMixin
from core.pagination import FlexiblePagination
from sites.api.serializers.option_serializers import (
    DepartmentOptionSerializer,
    LocationOptionSerializer,
    RoomOptionSerializer,
)
from sites.models.sites import Department, Location, Room


class DepartmentOptionViewSet(
    ScopeFilterMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Minimal scoped department options for frontend selectors.

    This endpoint is not a replacement for DepartmentViewSet.
    It returns lightweight option data only.

    Security model:
    - Requires authentication.
    - Uses ScopeFilterMixin to restrict results to the active role scope.
    - Does not expose retrieve/create/update/delete actions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentOptionSerializer
    pagination_class = FlexiblePagination

    queryset = (
        Department.objects
        .all()
        .order_by("name")
    )

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]

    search_fields = [
        "name",
    ]


class LocationOptionViewSet(
    ScopeFilterMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Minimal scoped location options for frontend selectors.

    This endpoint is not a replacement for LocationViewSet.
    It returns lightweight option data only.

    Optional filters:
    - department_id: department public_id

    Security model:
    - Requires authentication.
    - Uses ScopeFilterMixin to restrict results to the active role scope.
    - Does not expose retrieve/create/update/delete actions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = LocationOptionSerializer
    pagination_class = FlexiblePagination

    queryset = (
        Location.objects
        .select_related("department")
        .all()
        .order_by("name")
    )

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]

    search_fields = [
        "name",
        "department__name",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        department_id = self.request.query_params.get("department_id")

        if department_id:
            queryset = queryset.filter(
                department__public_id=department_id,
            )

        return queryset


class RoomOptionViewSet(
    ScopeFilterMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Minimal scoped room options for frontend selectors.

    This endpoint is not a replacement for RoomViewSet.
    It returns lightweight option data only.

    Optional filters:
    - department_id: department public_id
    - location_id: location public_id

    Security model:
    - Requires authentication.
    - Uses ScopeFilterMixin to restrict results to the active role scope.
    - Does not expose retrieve/create/update/delete actions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RoomOptionSerializer
    pagination_class = FlexiblePagination

    queryset = (
        Room.objects
        .select_related(
            "location",
            "location__department",
        )
        .all()
        .order_by("name")
    )

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]

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
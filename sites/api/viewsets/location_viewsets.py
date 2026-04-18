from rest_framework import viewsets
from db_inventory.serializers.equipment import EquipmentSerializer, EquipmentSerializer
from db_inventory.serializers.consumables import ConsumableAreaReaSerializer
from db_inventory.serializers.accessories import AccessoryFullSerializer
from db_inventory.models.assets import Equipment, Consumable, Accessory, Component, EquipmentStatus
from db_inventory.permissions.users import RolePermission, UserPermission
from assignments.api.serializers.assignment import EquipmentAssignmentSerializer
from assignments.models.asset_assignment import EquipmentAssignment
from users.models.roles import RoleAssignment
from users.api.serializers.roles import RoleReadSerializer
from users.api.serializers.users import UserAreaSerializer
from sites.api.serializers.locations import LocationComponentSerializer, LocationListSerializer, LocationReadSerializer, LocationRoomSerializer, LocationWriteSerializer
from sites.models.sites import Location, Room, UserPlacement
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import *
from db_inventory.mixins import AccessoryDashboardMixin, AreaDashboardMixin, ConsumableDashboardMixin, LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, RoleVisibilityMixin
from sites.permissions.sites import LocationPermission
from django.db.models import Case, When, Value, IntegerField
from db_inventory.pagination import FlexiblePagination
from django.db.models import Q
from db_inventory.mixins import AuditMixin
from rest_framework import mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count
from db_inventory.permissions.assets import AssetPermission, HasAssignmentScopePermission

class LocationDashboardView(AreaDashboardMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(location__public_id=public_id)

    def get(self, request, public_id):
        location = get_object_or_404(Location, public_id=public_id)
        return Response(self.build_dashboard(location))

class LocationViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Location objects"""

    lookup_field = "public_id"
    permission_classes = [LocationPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["^name", "name"]
    filterset_class = LocationFilter

    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return LocationWriteSerializer

        # Light list endpoint (unpaginated)
        if self.action == "list" and self.pagination_class is None:
            return LocationListSerializer

        return LocationReadSerializer

    def get_queryset(self):
        qs = Location.objects.all()
        search_term = self.request.query_params.get("search")

        if search_term:
            qs = qs.annotate(
                starts_with_order=Case(
                    When(name__istartswith=search_term, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).order_by("starts_with_order", "name")

        return qs

class LocationRoomsView(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of rooms in a given location"""
    serializer_class = LocationRoomSerializer
    lookup_field = "public_id"

    permission_classes = [LocationPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = RoomFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs["public_id"]

        qs = Room.objects.filter(location__public_id=location_id)


        return qs



class LocationUsersView(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of users in a given location"""
    serializer_class = UserAreaSerializer

    permission_classes = [UserPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["user__email"]
    filterset_class = AreaUserFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs["public_id"]

        qs = (
            UserPlacement.objects
            .filter(
                is_current=True,
                room__location__public_id=location_id,
            )
            .select_related(
                "user",
                "room",
            ).order_by("-id")
        )

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        return super().get_serializer(*args, **kwargs)
    
class LocationEquipmentView(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of equipment in a given location"""
    serializer_class = EquipmentSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = EquipmentFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs["public_id"]

        qs = (
            Equipment.objects
            .filter(room__location__public_id=location_id, is_deleted=False)
            .order_by("-id")
        )

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        return super().get_serializer(*args, **kwargs)

class LocationEquipmentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):

        equipment_qs = Equipment.objects.filter(
            room__location__public_id=public_id,is_deleted=False
        ).select_related(
            "room__location"
        )
        status_counts = (
            equipment_qs
            .values("status")
            .annotate(count=Count("id"))
        )

        status_map = {
            row["status"]: row["count"]
            for row in status_counts
        }

        total_equipment = sum(status_map.values())

        active_assignments = EquipmentAssignment.objects.filter(
            equipment__in=equipment_qs,
            returned_at__isnull=True
        ).count()


        available = equipment_qs.filter(
            status=EquipmentStatus.OK,
            active_assignment__returned_at__isnull=True
        ).count()

        return Response({
            "equipment_health": {
                "total": total_equipment,
                "available": available,
                "under_repair": status_map.get(EquipmentStatus.UNDER_REPAIR, 0),
                "damaged": status_map.get(EquipmentStatus.DAMAGED, 0),
                "lost": status_map.get(EquipmentStatus.LOST, 0),
            },
            "utilization": {
                "active_assignments": active_assignments,
                "percent_assigned": round(
                    (active_assignments / total_equipment * 100)
                    if total_equipment else 0,
                    1
                ),
            },
        })


class LocationConsumablesView(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of consumables in a given location"""
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = ConsumableFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs["public_id"]

        qs = (
            Consumable.objects
            .filter(room__location__public_id=location_id,is_deleted=False)
            .order_by("-id")
        )

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        return super().get_serializer(*args, **kwargs)

class LocationConsumableDashboardView( ConsumableDashboardMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        location = get_object_or_404(Location, public_id=public_id)
        return location.rooms.all()

    def get(self, request, public_id):
        rooms = self.get_rooms(public_id)
        period = self.get_period(request)

        data = self.build_dashboard_response(rooms, period)
        return Response(data)

    
class LocationAccessoriesView(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of accessories in a given location"""
    serializer_class = AccessoryFullSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = AccessoryFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs["public_id"]

        qs = (
            Accessory.objects
            .filter(room__location__public_id=location_id,is_deleted=False)
            .order_by("-id")
        )

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        return super().get_serializer(*args, **kwargs)
    

class LocationAccessoryDashboardView(
    AccessoryDashboardMixin,
    APIView
):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(
            location__public_id=public_id
        )

    def get(self, request, public_id):
        period = self.get_period(request)
        rooms = self.get_rooms(public_id)
        data = self.build_dashboard_response(rooms, period)
        return Response(data)
    
    


class LocationComponentsViewSet( ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    """Retrieves a list of components in a given location"""
    serializer_class = LocationComponentSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = ComponentFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs.get("public_id")

        if not location_id:
            return Component.objects.none()

        qs = (
            Component.objects
            .filter(
                equipment__room__location__public_id=location_id
            )
            .select_related(
                "equipment__room__location__department"
            )
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs


class LocationRolesViewSet(ScopeFilterMixin,RoleVisibilityMixin,viewsets.ReadOnlyModelViewSet):
    """
    Retrieves a list of users and their roles in a given location
    """
    queryset = RoleAssignment.objects.all()
    serializer_class = RoleReadSerializer
    lookup_field = "public_id"

    permission_classes = [RolePermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = RoleAssignmentFilter
    search_fields = ["role"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs.get("public_id")

        queryset = super().get_queryset().filter(
            Q(location__public_id=location_id) |
            Q(room__location__public_id=location_id)
        )

        queryset = self.filter_visibility(queryset)

        return queryset.order_by("-assigned_date")

class LocationEquipmentAssignmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EquipmentAssignmentSerializer

    permission_classes = [HasAssignmentScopePermission]

    def get_queryset(self):
        location_id = self.kwargs.get("public_id")

        return EquipmentAssignment.objects.select_related(
            "equipment",
            "equipment__room",
            "equipment__room__location",
            "equipment__room__location__department",
            "user",
            "assigned_by",
        ).filter(
            equipment__room__location__public_id=location_id
        )
from rest_framework import viewsets
from db_inventory.models import Consumable,  Equipment, Component, Accessory
from db_inventory.serializers.roles import RoleReadSerializer
from db_inventory.filters import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count  
from db_inventory.mixins import AccessoryDashboardMixin, AreaDashboardMixin, ConsumableDashboardMixin, LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, AuditMixin, RoleVisibilityMixin
from db_inventory.pagination import  FlexiblePagination

from db_inventory.serializers.equipment import EquipmentSerializer
from db_inventory.serializers.users import UserAreaSerializer
from db_inventory.serializers.consumables import ConsumableAreaReaSerializer
from db_inventory.serializers.accessories import AccessoryFullSerializer
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from db_inventory.models.assets import EquipmentStatus
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from db_inventory.permissions.assets import AssetPermission
from db_inventory.permissions.users import RolePermission, UserPermission
from assignments.api.serializers.assignment import EquipmentAssignmentSerializer
from sites.permissions.sites import DepartmentPermission, LocationPermission, RoomPermission
from sites.api.serializers.departments import DepartmentComponentSerializer, DepartmentListSerializer, DepartmentLocationsLightSerializer, DepartmentSerializer, DepartmentWriteSerializer
from sites.api.serializers.rooms import RoomSerializer

class DepartmentDashboardView(AreaDashboardMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(
            location__department__public_id=public_id
        )

    def get(self, request, public_id):
        department = get_object_or_404(Department, public_id=public_id)
        return Response(self.build_dashboard(department))

class DepartmentViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Department objects"""

    lookup_field = "public_id"
    permission_classes = [DepartmentPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = DepartmentFilter

    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return DepartmentWriteSerializer

        # Flat list endpoint (unpaginated)
        if self.action == "list" and self.pagination_class is None:
            return DepartmentListSerializer

        return DepartmentSerializer

    def get_queryset(self):
        return Department.objects.all().order_by("-id")

class DepartmentUsersViewSet(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    serializer_class = UserAreaSerializer
    permission_classes = [UserPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["user__email"]
    exclude_filter_fields = ["department"]
    filterset_class = AreaUserFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        qs = (
            UserPlacement.objects.filter(
                is_current=True,
                room__location__department__public_id=department_id
            )
            .select_related(
                "user",
                "room",
                "room__location",
                "room__location__department",
            )
            .order_by("-id")
        )

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        return super().get_serializer(*args, **kwargs)

class DepartmentLocationsViewSet(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    serializer_class = DepartmentLocationsLightSerializer
    permission_classes = [LocationPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = LocationFilter
    exclude_filter_fields = ["department"]

    pagination_class = FlexiblePagination
    lookup_field = "public_id"

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        qs = (
            Location.objects
            .filter(department__public_id=department_id)
            .annotate(room_count=Count("rooms"))
            .order_by("-id")
        )

        return qs

class DepartmentEquipmentViewSet(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    """Retrieves a list of equipment in a given department"""
    serializer_class = EquipmentSerializer
    lookup_field = "public_id"
    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = EquipmentFilter
    exclude_filter_fields = ["department"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        qs = (
            Equipment.objects
            .filter(room__location__department__public_id=department_id,
                is_deleted=False)
            .order_by("-id")
        )


        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        return super().get_serializer(*args, **kwargs)

class DepartmentEquipmentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):

        equipment_qs = Equipment.objects.filter(
            room__location__department__public_id=public_id,
                is_deleted=False
        ).select_related(
            "room__location__department"
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

        ok_unassigned = equipment_qs.filter(
            status=EquipmentStatus.OK,
            active_assignment__returned_at__isnull=True
        ).count()

        return Response({
            "equipment_health": {
                "total": total_equipment,
                "available": ok_unassigned,
                "under_repair": status_map.get(EquipmentStatus.UNDER_REPAIR, 0),
                "ok": status_map.get(EquipmentStatus.OK, 0),
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


class DepartmentConsumablesViewSet(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    """Retrieves a list of consumables in a given department"""
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = ConsumableFilter
    exclude_filter_fields = ["department"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        qs = (
            Consumable.objects
            .filter(room__location__department__public_id=department_id,
                is_deleted=False)
            .order_by("-id")
        )

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        return super().get_serializer(*args, **kwargs)
    
class DepartmentConsumableDashboardView( ConsumableDashboardMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(
            location__department__public_id=public_id
        )

    def get(self, request, public_id):
        rooms = self.get_rooms(public_id)
        period = self.get_period(request)

        data = self.build_dashboard_response(rooms, period)
        return Response(data)


class DepartmentAccessoriesViewSet(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    serializer_class = AccessoryFullSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = AccessoryFilter
    exclude_filter_fields = ["department"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        return (
            Accessory.objects
            .filter(
                room__location__department__public_id=department_id,
                is_deleted=False,
            )
            .select_related("room", "room__location", "room__location__department")
            .prefetch_related("assignments")
            .order_by("-id")
        )

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        return super().get_serializer(*args, **kwargs)
    

class DepartmentAccessoryDashboardView( AccessoryDashboardMixin, APIView ):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(
            location__department__public_id=public_id
        )

    def get(self, request, public_id):
        period = self.get_period(request)
        rooms = self.get_rooms(public_id)
        data = self.build_dashboard_response(rooms, period)
        return Response(data)
    


class DepartmentComponentsViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    """Retrieves a list of components in a given department"""
    serializer_class = DepartmentComponentSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = ComponentFilter
    exclude_filter_fields = ["department"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        qs = (
            Component.objects
            .filter(
                equipment__room__location__department__public_id=department_id
            )
            .order_by("-id")
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs
    
class DepartmentRolesViewSet(ScopeFilterMixin,RoleVisibilityMixin,viewsets.ReadOnlyModelViewSet):
    """
    Retrieves a list of users and their roles in a given department
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
        department_id = self.kwargs.get("public_id")

        # Base queryset: department + all children (locations + rooms)
        qs = super().get_queryset().filter(
            Q(department__public_id=department_id) |
            Q(location__department__public_id=department_id) |
            Q(room__location__department__public_id=department_id)
        )

        # Apply role visibility rules (peer hiding, rank visibility)
        qs = self.filter_visibility(qs)

        return qs.order_by("-id")
    

class DepartmentRoomsViewSet(LightEndpointMixin, ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet, ):
    serializer_class = RoomSerializer
    lookup_field = "public_id"

    permission_classes = [RoomPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = RoomFilter
    exclude_filter_fields = ["department", "location"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs["public_id"]

        qs = (
            Room.objects
            .filter(location__department__public_id=department_id)
            .select_related("location", "location__department")
            .order_by("location__name", "name")
        )

        return qs

class DepartmentEquipmentAssignmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    # permission_classes = [IsDepartmentAdmin]
    serializer_class = EquipmentAssignmentSerializer

    def get_queryset(self):
        department_id = self.kwargs.get("public_id")

        return EquipmentAssignment.objects.select_related(
            "equipment",
            "equipment__room",
            "equipment__room__location",
            "equipment__room__location__department",
            "user",
            "assigned_by",
        ).filter(
            equipment__room__location__department__public_id=department_id
        )
from rest_framework import viewsets
from db_inventory.serializers.rooms import  *
from db_inventory.serializers.assignment import EquipmentAssignmentSerializer
from db_inventory.models import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import *
from db_inventory.permissions import RoomPermission, AssetPermission, UserPermission
from db_inventory.mixins import AccessoryDashboardMixin, AreaDashboardMixin, ConsumableDashboardMixin, ScopeFilterMixin, AuditMixin, ExcludeFiltersMixin, RoleVisibilityMixin
from django.db.models import Case, When, Value, IntegerField
from db_inventory.pagination import FlexiblePagination
from db_inventory.serializers import *
from django.db.models import Q
from rest_framework import mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from db_inventory.models.assets import EquipmentStatus
from django.db.models import Count
from django.shortcuts import get_object_or_404


class RoomDashboardView(AreaDashboardMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(public_id=public_id)

    def get(self, request, public_id):
        room = get_object_or_404(Room, public_id=public_id)
        return Response(self.build_dashboard(room))
    
class RoomViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet):
    lookup_field = "public_id"
    permission_classes = [RoomPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["^name", "name"]
    filterset_class = RoomFilter

    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RoomWriteSerializer

        # Light list endpoint
        if self.action == "list" and self.pagination_class is None:
            return RoomListSerializer

        return RoomReadSerializer
    
    def get_queryset(self):
        qs = Room.objects.all().order_by("id")
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

    
class RoomUsersViewSet( ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of users in a given room"""
    serializer_class = UserAreaSerializer
    lookup_field = "public_id"

    permission_classes = [UserPermission]

    filter_backends = [DjangoFilterBackend]
    filterset_class = AreaUserFilter
    exclude_filter_fields = ["department", "location", "room"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs["public_id"]

        qs = (
            UserLocation.objects
            .filter(
                is_current=True,
                room__public_id=room_id,
            )
            .select_related(
                "user",
                "room",
            )
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        kwargs["exclude_room"] = True
        return super().get_serializer(*args, **kwargs)
    
class RoomEquipmentViewSet( ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of equipment in a given room"""
    serializer_class = EquipmentSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = EquipmentFilter
    exclude_filter_fields = ["department", "location", "room"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs["public_id"]

        qs = (
            Equipment.objects
            .filter(room__public_id=room_id,
                is_deleted=False)
            .order_by("-id")
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        kwargs["exclude_room"] = True
        return super().get_serializer(*args, **kwargs)
    

class RoomEquipmentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        # ---------------------------------------------
        # 1. Base queryset: all equipment in the room
        # ---------------------------------------------
        equipment_qs = Equipment.objects.filter(
            room__public_id=public_id
        ).select_related(
            "room"
        )

        # ---------------------------------------------
        # 2. Equipment status aggregation
        # ---------------------------------------------
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

        # ---------------------------------------------
        # 3. Active assignments
        # ---------------------------------------------
        active_assignments = EquipmentAssignment.objects.filter(
            equipment__in=equipment_qs,
            returned_at__isnull=True
        ).count()

        # ---------------------------------------------
        # 4. Available equipment
        # (OK + not currently assigned)
        # ---------------------------------------------
        available = equipment_qs.filter(
            status=EquipmentStatus.OK,
            active_assignment__returned_at__isnull=True
        ).count()

        # ---------------------------------------------
        # 5. Response
        # ---------------------------------------------
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
    

class RoomConsumablesViewSet( ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of consumables in a given room"""
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = ConsumableFilter
    exclude_filter_fields = ["department", "location", "room"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs["public_id"]

        qs = (
            Consumable.objects
            .filter(room__public_id=room_id)
            .order_by("-id")
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        kwargs["exclude_room"] = True
        return super().get_serializer(*args, **kwargs)
    
class RoomConsumableDashboardView( ConsumableDashboardMixin, APIView, ):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        room = get_object_or_404(Room, public_id=public_id)
        return Room.objects.filter(id=room.id)

    def get(self, request, public_id):
        rooms = self.get_rooms(public_id)
        period = self.get_period(request)

        data = self.build_dashboard_response(rooms, period)
        return Response(data)   

class RoomAccessoriesViewSet( ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of accessories in a given room"""
    serializer_class = AccessoryFullSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = AccessoryFilter
    exclude_filter_fields = ["department", "location", "room"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs["public_id"]

        qs = (
            Accessory.objects
            .filter(room__public_id=room_id)
            .order_by("-id")
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs

    def get_serializer(self, *args, **kwargs):
        kwargs["exclude_department"] = True
        kwargs["exclude_location"] = True
        kwargs["exclude_room"] = True
        return super().get_serializer(*args, **kwargs)
    
class RoomAccessoryDashboardView(
    AccessoryDashboardMixin,
    APIView
):
    permission_classes = [IsAuthenticated]

    def get_rooms(self, public_id):
        return Room.objects.filter(
            public_id=public_id
        )

    def get(self, request, public_id):
        period = self.get_period(request)
        rooms = self.get_rooms(public_id)
        data = self.build_dashboard_response(rooms, period)
        return Response(data)

class RoomComponentsViewSet( ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet, ):
    """Retrieves a list of components in a given room"""
    serializer_class = ComponentSerializer
    lookup_field = "public_id"

    permission_classes = [AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]
    filterset_class = ComponentFilter
    exclude_filter_fields = ["department", "location", "room"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs["public_id"]

        qs = (
            Component.objects
            .filter(equipment__room__public_id=room_id)
            .order_by("-id")
        )

        # Light endpoint → unpaginated + capped
        if self.pagination_class is None:
            qs = qs[:20]

        return qs
    


class RoomRolesViewSet(ScopeFilterMixin,RoleVisibilityMixin,viewsets.ReadOnlyModelViewSet):
    """
    Retrieves a list of users and their roles in a given room
    """

    queryset = RoleAssignment.objects.all()
    serializer_class = RoleReadSerializer
    lookup_field = "public_id"

    permission_classes = [RoomPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = RoleAssignmentFilter
    search_fields = ["role"]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs.get("public_id")

        # Base filter: roles assigned directly to this room
        qs = super().get_queryset().filter(
            room__public_id=room_id
        )

        # Apply role visibility rules (peer hiding, rank visibility)
        qs = self.filter_visibility(qs)

        return qs.order_by("-id")

class RoomEquipmentAssignmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EquipmentAssignmentSerializer

    def get_queryset(self):
        room_id = self.kwargs.get("public_id")

        return EquipmentAssignment.objects.select_related(
            "equipment",
            "equipment__room",
            "equipment__room__location",
            "equipment__room__location__department",
            "user",
            "assigned_by",
        ).filter(
            equipment__room__public_id=room_id
        )
from rest_framework import viewsets
from db_inventory.serializers.rooms import  *
from db_inventory.serializers.assignment import EquipmentAssignmentSerializer
from db_inventory.models import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import *
from db_inventory.permissions import RoomPermission, AssetPermission, UserPermission
from db_inventory.mixins import AccessoryDashboardMixin, ScopeFilterMixin, AuditMixin, ExcludeFiltersMixin, RoleVisibilityMixin
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

class RoomModelViewSet(AuditMixin,ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Room objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Room objects."""
        
    queryset = Room.objects.all().order_by("id")
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    pagination_class = FlexiblePagination

    filterset_class = RoomFilter

    permission_classes = [RoomPermission]


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoomWriteSerializer
        return RoomReadSerializer
    

    def get_queryset(self):
        qs = super().get_queryset()
        search_term = self.request.query_params.get('search', None)

        if search_term:
            # Annotate results: 1 if starts with search_term, 2 otherwise
            qs = qs.annotate(
                starts_with_order=Case(
                    When(name__istartswith=search_term, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).order_by('starts_with_order', 'name')  # starts-with results first

        return qs
    

        
class RoomListViewset(ScopeFilterMixin, viewsets.ModelViewSet):
   
    queryset = Room.objects.all()
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [SearchFilter]
    search_fields = ['name']

    serializer_class = RoomListSerializer

    permission_classes = [RoomPermission]

    
class RoomUsersViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of users in a given room"""
    serializer_class = UserAreaSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend]
    filterset_class = AreaUserFilter

    pagination_class = FlexiblePagination

    exclude_filter_fields = ["department", "location", "room"]

    permission_classes = [UserPermission]
    


    def get_queryset(self):
        room_id = self.kwargs.get("public_id")

        return (
            UserLocation.objects.filter(
                is_current=True,
                room__public_id=room_id,
            )
            .select_related(
                "user",
                "room",
            )
        )
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)

class RoomEquipmentViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given room"""
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = EquipmentFilter

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]


    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__public_id=room_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
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
    

class RoomConsumablesViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given room"""
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = ConsumableFilter

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]


    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__public_id=room_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)
    
    

class RoomAccessoriesViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given room"""
    serializer_class = AccessoryFullSerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department", "location", "room"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__public_id=room_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
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

class RoomComponentsViewSet(ScopeFilterMixin,ExcludeFiltersMixin,viewsets.ModelViewSet):
    """Retrieves a list of components in a given room"""
    serializer_class = ComponentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = ComponentFilter

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__public_id=room_id).order_by('-id')
    

class RoomComponentsMiniViewSet(ScopeFilterMixin,viewsets.ReadOnlyModelViewSet):
    serializer_class = ComponentSerializer
    lookup_field = 'public_id'
    pagination_class = None
    permission_classes = [AssetPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__public_id=room_id).order_by('-id')[:20]


class RoomUsersMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAreaSerializer
    lookup_field = 'public_id'
    pagination_class = None
    permission_classes = [UserPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(room__public_id=room_id)
            .select_related('user', 'room')
            .order_by('-id')[:20]
        )
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)
    

class RoomEquipmentMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None
    permission_classes = [AssetPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__public_id=room_id).order_by('-id')[:20]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)


class RoomConsumablesMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'
    pagination_class = None
    permission_classes = [AssetPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__public_id=room_id).order_by('-id')[:20]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)


class RoomAccessoriesMiniViewSet(ScopeFilterMixin,viewsets.ReadOnlyModelViewSet):
    serializer_class = AccessoryFullSerializer
    lookup_field = 'public_id'
    pagination_class = None
    permission_classes = [AssetPermission]

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__public_id=room_id).order_by('-id')[:20]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)


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
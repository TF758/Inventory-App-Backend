from rest_framework import viewsets
from db_inventory.models import Consumable, Department, Location, Equipment, Component, Accessory, UserLocation, Room
from db_inventory.serializers.roles import RoleReadSerializer
from db_inventory.serializers.assignment import EquipmentAssignmentSerializer
from db_inventory.filters import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count  
from db_inventory.mixins import ScopeFilterMixin, ExcludeFiltersMixin, AuditMixin, RoleVisibilityMixin
from db_inventory.permissions import DepartmentPermission, UserPermission, LocationPermission, AssetPermission, RolePermission, RoomPermission
from db_inventory.pagination import  FlexiblePagination
from django.db.models import Q
from db_inventory.serializers.departments import *
from db_inventory.serializers.equipment import EquipmentSerializer
from db_inventory.serializers.users import UserAreaSerializer
from db_inventory.serializers.consumables import ConsumableAreaReaSerializer
from db_inventory.serializers.accessories import AccessoryFullSerializer
from db_inventory.serializers.rooms import RoomSerializer
from django.contrib.contenttypes.models import ContentType
from rest_framework import mixins



class DepartmentModelViewSet(AuditMixin,ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Department objects.
    This viewset provides `list`, `create`, actions for Department objects."""

    queryset = Department.objects.all().order_by('-id')
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    permission_classes=[DepartmentPermission]

    pagination_class = FlexiblePagination
    

    filterset_class = DepartmentFilter
    

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DepartmentWriteSerializer
        return DepartmentSerializer

class DepartmentListViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):

    """Returns a flat list of department objects"""

    queryset = Department.objects.all()
    lookup_field = 'public_id'

    permission_classes=[DepartmentPermission]

    filter_backends = [SearchFilter]
    search_fields = ['name']
    pagination_class = None 

    serializer_class = DepartmentListSerializer



class DepartmentUsersViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    """Retrieves a list of users in a given department"""
    serializer_class = UserAreaSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['user__email']
    exclude_filter_fields = ["department"]

    permission_classes=[UserPermission]


    filterset_class = AreaUserFilter

    pagination_class = FlexiblePagination

    
    def get_queryset(self):
        department_id = self.kwargs.get("public_id")

        return (
            UserLocation.objects.filter(is_current=True)
            .filter(
                Q(room__location__department__public_id=department_id)
                | Q(
                    user__created_by__user_locations__is_current=True,
                    user__created_by__user_locations__room__location__department__public_id=department_id
                )
                | Q(user__role_assignments__department__public_id=department_id)
            )
            .select_related(
                "user",
                "room",
                "room__location",
                "room__location__department",
            )
            .distinct()
            .order_by("-id")
        )

    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)
    
    
class DepartmentUsersMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    Lightweight, read-only version for dashboard:
    last 20 users of a department, ordered by most recent (-id).
    Pagination disabled.
    """
    serializer_class = UserAreaSerializer
    pagination_class = None  # disables global pagination

    permission_classes=[UserPermission]

    def get_queryset(self):
        department_id = self.kwargs.get("public_id")

        return (
            UserLocation.objects.filter(is_current=True)
            .filter(
                Q(room__location__department__public_id=department_id)
                | Q(
                    user__created_by__user_locations__is_current=True,
                    user__created_by__user_locations__room__location__department__public_id=department_id
                )
                | Q(user__role_assignments__department__public_id=department_id)
            )
            .select_related(
                "user",
                "room",
                "room__location",
                "room__location__department",
            )
            .distinct()
            .order_by("-id")
        )

class DepartmentLocationsViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    serializer_class = DepartmentLocationsLightSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]

    search_fields = ['name']
    filterset_class = LocationFilter
    exclude_filter_fields = ["department"]

    permission_classes=[LocationPermission]

    pagination_class = FlexiblePagination

    lookup_field = 'public_id'


    def get_queryset(self):
        department_id = self.kwargs.get("public_id")

        return (
            Location.objects
            .filter(department__public_id=department_id)
            .annotate(room_count=Count('rooms'))  
            
        )

class DepartmentLocationsMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentLocationsLightSerializer
    lookup_field = 'public_id'
    pagination_class = None  # disable global pagination
    permission_classes=[LocationPermission]

    def get_queryset(self):
        department_id = self.kwargs.get("public_id")
        return (
            Location.objects.filter(department__public_id=department_id)
            .annotate(room_count=Count('rooms'))
            .order_by('-id')[:20]  # last 20 locations
        )


class DepartmentEquipmentViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    """Retrieves a list of equipment in a given department"""
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'

    permission_classes=[AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department"]

    filterset_class = EquipmentFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__location__department__public_id=department_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)
    


class DepartmentEquipmentMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    permission_classes=[AssetPermission]

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Equipment.objects.filter(room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )
    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)


class DepartmentConsumablesViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    """Retrieves a list of consumables in a given department"""
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    permission_classes=[AssetPermission]

    exclude_filter_fields = ["department"]

    filterset_class = ConsumableFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__location__department__public_id=department_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)
    


class DepartmentConsumablesMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'
    pagination_class = None

    permission_classes=[AssetPermission]

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Consumable.objects.filter(room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )
    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)

class DepartmentAccessoriesViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of accessories in a given department"""
    serializer_class = AccessoryFullSerializer
    lookup_field = 'public_id'

    permission_classes=[AssetPermission]

    filterset_class = AccessoryFilter

    exclude_filter_fields = ["department"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    pagination_class = FlexiblePagination

 
    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__location__department__public_id=department_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)
    

class DepartmentAccessoriesMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AccessoryFullSerializer
    lookup_field = 'public_id'
    pagination_class = None

    permission_classes=[AssetPermission]

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Accessory.objects.filter(room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )

    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        return super().get_serializer(*args, **kwargs)    

class DepartmentComponentsViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of components in a given department"""
    serializer_class = DepartmentComponentSerializer
    lookup_field = 'public_id'

    permission_classes=[AssetPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department"]

    filterset_class = ComponentFilter

    pagination_class = FlexiblePagination
    


    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__location__department__public_id=department_id).order_by('-id')
    
    

class DepartmentComponentsMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentComponentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    permission_classes=[AssetPermission]

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Component.objects.filter(equipment__room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )
    

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
    

class DepartmentRoomsViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    serializer_class = RoomSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]

    search_fields = ['name']
    filterset_class = RoomFilter
    exclude_filter_fields = ["department", "location"]

    permission_classes=[RoomPermission]

    pagination_class = FlexiblePagination

    lookup_field = 'public_id'


    def get_queryset(self):
        department_id = self.kwargs.get("public_id")

        return (
            Room.objects
            .filter(location__department__public_id=department_id)
            .select_related("location", "location__department") 
            .order_by("location__name", "name")
        )

# ASSIGNMENT

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
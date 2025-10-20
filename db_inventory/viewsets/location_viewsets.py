from rest_framework import viewsets
from ..serializers.locations import *
from ..serializers.equipment import EquipmentSerializer
from ..serializers import *
from ..serializers.roles import RoleReadSerializer
from ..models import Location, Room, UserLocation, Equipment, Consumable, Accessory, Component, RoleAssignment
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import LocationFilter, RoomFilter, ConsumableFilter, EquipmentFilter, AccessoryFilter, AreaUserFilter, ComponentFilter
from ..utils import ExcludeFiltersMixin
from ..mixins import ScopeFilterMixin
from ..permissions import LocationPermission
from django.db.models import Case, When, Value, IntegerField
from ..pagination import BasePagination, FlexiblePagination
from django.db.models import Q

class LocationModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Location objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Location objects."""

    queryset = Location.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    permission_classes =[LocationPermission]

    filterset_class = LocationFilter

    pagination_class = FlexiblePagination

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return LocationWriteSerializer
        return LocationReadSerializer
    

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
    
class LocationListViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

    """Returns a flat list of location objects"""

    queryset = Location.objects.all()
    lookup_field = 'public_id'
    pagination_class = None 

    filter_backends = [SearchFilter]
    search_fields = ['name']

    permission_classes =[LocationPermission]

    serializer_class = LocationListSerializer 

class LocationRoomsView(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of rooms in a given location"""
    serializer_class = LocationRoomSerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department", "location"]

    permission_classes =[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Room.objects.filter(location__public_id=location_id)

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = RoomFilter

    pagination_class = FlexiblePagination


class LocationRoomsMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationRoomSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    permission_classes =[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Room.objects.filter(location__public_id=location_id)


class LocationUsersView(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of users in a given location"""
    serializer_class = UserAreaSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['user__email']

    exclude_filter_fields = ["department", "location"]

    filterset_class =  AreaUserFilter

    permission_classes =[LocationPermission]

    pagination_class = FlexiblePagination
    

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(
                room__location__public_id=location_id
            )
            .select_related(
                'user',
                'room',
            )
        )
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)

    
class LocationUsersMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAreaSerializer
    pagination_class = None

    permission_classes =[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(room__location__public_id=location_id)
            .select_related('user', 'room')
            .order_by('-id')[:20]
        )

class LocationEquipmentView(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given location"""
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department", "location"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter

    permission_classes =[LocationPermission]

    pagination_class = FlexiblePagination


    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__location__public_id=location_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)
    
class LocationEquipmentMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    permission_classes =[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__location__public_id=location_id).order_by('-id')[:20]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)


class LocationConsumablesView(ScopeFilterMixin, ExcludeFiltersMixin,viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given location"""
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location"]

    filterset_class = ConsumableFilter

    permission_classes =[LocationPermission]

    pagination_class = FlexiblePagination


    def get_queryset(self):
        location_id = self.kwargs.get('public_id')

        return Consumable.objects.filter(room__location__public_id=location_id).order_by('-id')
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)
    
class LocationConsumablesMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    permission_classes =[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__location__public_id=location_id).order_by('-id')[:20]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)
    
    
    
class LocationAccessoriesView(ScopeFilterMixin,ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given location"""
    serializer_class = AccessoryFullSerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department", "location"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    permission_classes =[LocationPermission]

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__location__public_id=location_id).order_by('-id')
    

    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)
    

class LocationAccessoriesMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AccessoryFullSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    permission_classes =[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__location__public_id=location_id).order_by('-id')[:20]
    
    def get_serializer(self, *args, **kwargs):
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        return super().get_serializer(*args, **kwargs)
    


class LocationComponentsViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of components in a given location"""
    serializer_class = LocationComponentSerializer
    lookup_field = 'public_id'

    permission_classes=[LocationPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location"]

    filterset_class = ComponentFilter

    pagination_class = FlexiblePagination
    
    def get_queryset(self):
        location_id = self.kwargs.get("public_id")

        if not location_id:
            return Component.objects.none()

        return Component.objects.filter(
            equipment__room__location__public_id=location_id
        ).select_related(
            "equipment__room__location__department" 
        )
    
class LocationComponentsMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationComponentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    permission_classes=[LocationPermission]

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return (
            Component.objects.filter(equipment__room__location__public_id=location_id)
            .order_by('-id')[:20]
        )

class LocationRolesViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of users and thier roles in a given location"""
    serializer_class = RoleReadSerializer
    lookup_field = 'public_id'

    permission_classes=[LocationPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['role']

    # filterset_class = RoleFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')

        return RoleAssignment.objects.filter(
            Q(location__public_id=location_id) |
            Q(room__location__public_id=location_id)
        ).order_by('-id')
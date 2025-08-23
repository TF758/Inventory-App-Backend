from rest_framework import viewsets
from ..serializers.locations import *

from ..models import Location, Room, UserLocation, Equipment, Consumable, Accessory
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import LocationFilter, RoomFilter, ConsumableFilter, EquipmentFilter, AccessoryFilter


class LocationModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Location objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Location objects."""

    queryset = Location.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = LocationFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return LocationWriteSerializer
        return LocationReadSerializer
    

class LocationRoomsView(viewsets.ModelViewSet):
    """Retrieves a list of rooms in a given location"""
    serializer_class = LocationRoomSerializer
    lookup_field = 'public_id'

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Room.objects.filter(location__public_id=location_id)

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = RoomFilter


class LocationRoomsMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationRoomSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Room.objects.filter(location__public_id=location_id)


class LocationUsersView(viewsets.ModelViewSet):
    """Retrieves a list of users in a given location"""
    serializer_class = LocationUserLightSerializer

    filter_backends = [DjangoFilterBackend]
    # filterset_class = LocationUserFilter
    

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
    
class LocationUsersMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationUserLightSerializer
    pagination_class = None

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(room__location__public_id=location_id)
            .select_related('user', 'room')
            .order_by('-id')[:20]
        )

class LocationEquipmentView(viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given location"""
    serializer_class = LocationEquipmentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter


    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__location__public_id=location_id)
    
class LocationEquipmentMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationEquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__location__public_id=location_id).order_by('-id')[:20]


class LocationConsumablesView(viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given location"""
    serializer_class = LocationConsumableSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter


    def get_queryset(self):
        location_id = self.kwargs.get('public_id')

        print(Location.objects.filter(public_id=location_id).exists())

        return Consumable.objects.filter(room__location__public_id=location_id)
    
class LocationConsumablesMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationConsumableSerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__location__public_id=location_id).order_by('-id')[:20]
    
class LocationAccessoriesView(viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given location"""
    serializer_class = LocationAccessorySerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__location__public_id=location_id)
    

class LocationAccessoriesMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LocationAccessorySerializer
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        location_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__location__public_id=location_id).order_by('-id')[:20]
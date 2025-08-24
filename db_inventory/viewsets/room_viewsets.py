from rest_framework import viewsets
from ..serializers.rooms import  *
from ..models import Room, Equipment, Consumable,Accessory,Component,UserLocation
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import ComponentFilter, EquipmentFilter, ConsumableFilter,AccessoryFilter,RoomFilter
from ..utils import ExcludeFiltersMixin


class RoomModelViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Room objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Room objects."""
        
    queryset = Room.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = RoomFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoomWriteSerializer
        return RoomReadSerializer
    
class RoomListViewset(viewsets.ModelViewSet):
   
    queryset = Room.objects.all()
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [SearchFilter]
    search_fields = ['name']

    serializer_class = RoomListSerializer

    
class RoomUsersViewSet(viewsets.ModelViewSet):
    """Retrieves a list of users in a given room"""
    serializer_class = RoomUserLightSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend]
    # filterset_class = RoomUserFilter
    


    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(
                room__public_id=room_id
            )
            .select_related(
                'user',
                'room',
            )
        )
        

class RoomEquipmentViewSet(ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given room"""
    serializer_class = RoomEquipmentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = EquipmentFilter

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__public_id=room_id)
    

class RoomConsumablesViewSet(ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given room"""
    serializer_class = RoomConsumableSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = ConsumableFilter

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__public_id=room_id)
    

class RoomAccessoriesViewSet(ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given room"""
    serializer_class = RoomAccessorySerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department", "location", "room"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__public_id=room_id)
    

class RoomComponentsViewSet(ExcludeFiltersMixin,viewsets.ModelViewSet):
    """Retrieves a list of components in a given room"""
    serializer_class = RoomComponentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = ComponentFilter

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__public_id=room_id)



class RoomUsersMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomUserLightSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(room__public_id=room_id)
            .select_related('user', 'room')
            .order_by('-id')[:20]
        )


class RoomEquipmentMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomEquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__public_id=room_id).order_by('-id')[:20]


class RoomConsumablesMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomConsumableSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__public_id=room_id).order_by('-id')[:20]


class RoomAccessoriesMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomAccessorySerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__public_id=room_id).order_by('-id')[:20]


class RoomComponentsMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomComponentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__public_id=room_id).order_by('-id')[:20]
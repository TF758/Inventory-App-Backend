from rest_framework import viewsets
from ..serializers.rooms import  *
from ..models import Room, Equipment, Consumable,Accessory,Component,UserLocation
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import ComponentFilter, EquipmentFilter, ConsumableFilter,AccessoryFilter,RoomFilter


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
    
class RoomUsersView(viewsets.ModelViewSet):
    """Retrieves a list of users in a given room"""
    serializer_class = RoomUserLightSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend]
    # filterset_class = RoomUserFilter
    


    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return (
            UserLocation.objects.filter(
                room_id=room_id
            )
            .select_related(
                'user',
                'room',
            )
        )

class RoomEquipmentView(viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given room"""
    serializer_class = RoomEquipmentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Equipment.objects.filter(room_id=room_id)
    

class RoomConsumablesView(viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given room"""
    serializer_class = RoomConsumableSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Consumable.objects.filter(room_id=room_id)
    

class RoomAccessoriesView(viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given room"""
    serializer_class = RoomAccessorySerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Accessory.objects.filter(room_id=room_id)
    

class RoomComponentsView(viewsets.ModelViewSet):
    """Retrieves a list of components in a given room"""
    serializer_class = RoomComponentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ComponentFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Component.objects.filter(equipment__room_id=room_id)

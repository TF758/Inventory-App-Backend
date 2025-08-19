from django.shortcuts import render
from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Consumable, User, Department, Location, Equipment, Component, Accessory, UserLocation, Room
from .serializers import *
from django.views.generic.detail import SingleObjectMixin
from rest_framework.generics import ListAPIView
from .filters import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count  


class UserModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing User objects.
This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for User objects."""

    queryset = User.objects.all().order_by('-id')
    serializer_class = UserSerializerPrivate
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['email']

    filterset_class = UserFilter

class DepartmentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Department objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Department objects."""

    queryset = Department.objects.all()
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = DepartmentFilter
    

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DepartmentWriteSerializer
        return DepartmentSerializer

class DepartmentUsersView(viewsets.ModelViewSet):
    """Retrieves a list of users in a given department"""
    serializer_class = DepartmentUserLightSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend]
    filterset_class = DepartmentUserFilter
    


    def get_queryset(self):
        department_id = self.kwargs.get('department_id')
        return (
            UserLocation.objects.filter(
                room__location__department__id=department_id
            )
            .select_related(
                'user',
                'room',
                'room__location',
                'room__location__department'
            )
        )

class DepartmentLocationsView(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentLocationsLightSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    filterset_class = LocationFilter

    def get_queryset(self):
        department_id = self.kwargs.get("department_id")

        return (
            Location.objects
            .filter(department_id=department_id)
            .annotate(room_count=Count('rooms'))  
        )

class DepartmentEquipmentView(viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given department"""
    serializer_class = DepartmentEquipmentSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter

    def get_queryset(self):
        department_id = self.kwargs.get('department_id')
        return Equipment.objects.filter(room__location__department__id=department_id)
    

    def get_filterset(self, *args, **kwargs):
        filterset = super().get_filterset(*args, **kwargs)
        filterset.filters.pop("department", None)
        return filterset
    

class DepartmentConsumablesView(viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given department"""
    serializer_class = DepartmentConsumableSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter

    def get_queryset(self):
        department_id = self.kwargs.get('department_id')
        return Consumable.objects.filter(room__location__department__id=department_id)
    

class DepartmentAccessoriesView(viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given department"""
    serializer_class = DepartmentAccessorySerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

 

    def get_queryset(self):
        department_id = self.kwargs.get('department_id')
        return Accessory.objects.filter(room__location__department__id=department_id)

class LocationModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Location objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Location objects."""

    queryset = Location.objects.all()
    lookup_field = 'id'

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
    lookup_field = 'id'

    def get_queryset(self):
        location_id = self.kwargs.get('location_id')
        return Room.objects.filter(location_id=location_id)

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = RoomFilter


class LocationUsersView(viewsets.ModelViewSet):
    """Retrieves a list of users in a given location"""
    serializer_class = LocationUserLightSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend]
    # filterset_class = LocationUserFilter
    


    def get_queryset(self):
        location_id = self.kwargs.get('location_id')
        return (
            UserLocation.objects.filter(
                room__location__id=location_id
            )
            .select_related(
                'user',
                'room',
            )
        )


class LocationEquipmentView(viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given location"""
    serializer_class = LocationEquipmentSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter


    def get_queryset(self):
        location_id = self.kwargs.get('location_id')
        return Equipment.objects.filter(room__location_id=location_id)
    

class LocationConsumablesView(viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given location"""
    serializer_class = LocationConsumableSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter


    def get_queryset(self):
        location_id = self.kwargs.get('location_id')
        return Consumable.objects.filter(room__location_id=location_id)
    
class LocationAccessoriesView(viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given location"""
    serializer_class = LocationAccessorySerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_queryset(self):
        location_id = self.kwargs.get('location_id')
        return Accessory.objects.filter(room__location_id=location_id)

class RoomModelViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Room objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Room objects."""
        
    queryset = Room.objects.all()
    lookup_field = 'id'

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
    lookup_field = 'id'

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
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Equipment.objects.filter(room_id=room_id)
    

class RoomConsumablesView(viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given room"""
    serializer_class = RoomConsumableSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Consumable.objects.filter(room_id=room_id)
    

class RoomAccessoriesView(viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given room"""
    serializer_class = RoomAccessorySerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Accessory.objects.filter(room_id=room_id)
    

class RoomComponentsView(viewsets.ModelViewSet):
    """Retrieves a list of components in a given room"""
    serializer_class = RoomComponentSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ComponentFilter

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return Component.objects.filter(equipment__room_id=room_id)


class EquipmentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Equipment objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Equipment objects."""

    queryset = Equipment.objects.all()
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = EquipmentFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EquipmentWriteSerializer
        return EquipmentReadSerializer



class ComponentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Component objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Component objects."""

    queryset = Component.objects.all()
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ComponentFilter


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ComponentWriteSerializer
        return ComponentReadSerializer


class AccessoryModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Accessory objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Accessory objects."""

    queryset = Accessory.objects.all()
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AccessoryWriteSerializer
        return AccessoryReadSerializer


class ConsumableModelViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Consumable objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Consumable objects."""
    
    queryset = Consumable.objects.all()
    serializer_class = ConsumableSerializer
    lookup_field = 'id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = ConsumableFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ConsumableWriteSerializer
        return ConsumableReadSerializer
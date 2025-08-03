from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Consumable, User, Department, Location, Equipment, Component, Accessory, UserLocation, Room
from .serializers import *
from django.views.generic.detail import SingleObjectMixin
from rest_framework.generics import RetrieveUpdateAPIView
from .filters import EquipmentFilter, LocationFilter, ComponentFilter, AccessoryFilter, ConsumableFilter, RoomFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter



class UserModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing User objects.
This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for User objects."""

    queryset = User.objects.all().order_by('-id')
    serializer_class = UserSerializerPrivate
    lookup_field = 'id'

    # def get_permissions(self):
    #     if self.action == 'create':
    #         permission_classes = [IsAuthenticated]
    #     elif self.action == 'list':
    #         permission_classes = [AllowAny]
    #     elif self.action in ['update', 'partial_update', 'destroy']:
    #         permission_classes = [IsAuthenticated]
    #     else:
    #         permission_classes = [IsAuthenticated]
    #     return [permission() for permission in permission_classes]

class DepartmentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Department objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Department objects."""

    queryset = Department.objects.all()
    lookup_field = 'id'
    

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DepartmentWriteSerializer
        return DepartmentReadSerializer


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
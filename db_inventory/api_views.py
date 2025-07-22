from django.shortcuts import render
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Consumable, User, Department, Location, Equipment, Component, Accessory, UserLocation
from .serializers import ConsumableSerializer, UserSerializerPrivate, DepartmentSerializer, LocationSerializer,EquipmentSerializer, ComponentSerializer, AccessorySerializer, UserLocationSerializer
from django.views.generic.detail import SingleObjectMixin
from rest_framework.generics import RetrieveUpdateAPIView





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
    serializer_class = DepartmentSerializer
    lookup_field = 'id'

# class UsersLocationView(generics.ListAPIView): 
#     """
#     View to list all users in a specific department.
#     """
#     serializer_class = UserLocationSerializer

#     def get_queryset(self):
#         department_id = self.kwargs['id']
#         return UserLocation.objects.filter(department__id=department_id)


class LocationModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Location objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Location objects."""

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    lookup_field = 'id'


# class LocationEquipmentsView(generics.ListAPIView):
#     """
#     View to list all equipments in a specific location.
#     """
#     serializer_class = EquipmentSerializer

#     def get_queryset(self):
#         location_id = self.kwargs['id']
#         return Equipment.objects.filter(location__id=location_id)


class EquipmentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Equipment objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Equipment objects."""

    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    lookup_field = 'id'


class ComponentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Component objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Component objects."""

    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    lookup_field = 'id'

# class ComponentEquipmentsView(generics.ListAPIView):
#     """
#     View to list all equipments associated with a specific component.
#     """
#     serializer_class = EquipmentSerializer

#     def get_queryset(self):
#         component_id = self.kwargs['id']
#         return Equipment.objects.filter(components__id=component_id)


class AccessoryModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Accessory objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Accessory objects."""

    queryset = Accessory.objects.all()
    serializer_class = AccessorySerializer
    lookup_field = 'id'


class ConsumableModelViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Consumable objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Consumable objects."""
    
    queryset = Consumable.objects.all()
    serializer_class = ConsumableSerializer
    lookup_field = 'id'
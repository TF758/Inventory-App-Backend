from django.shortcuts import render
from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from ..models import Consumable, User, Department, Location, Equipment, Component, Accessory, UserLocation, Room
from ..serializers import *
from django.views.generic.detail import SingleObjectMixin
from rest_framework.generics import ListAPIView
from ..filters import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count  
from ..utils import ExcludeFiltersMixin


class DepartmentModelViewSet(viewsets.ModelViewSet):

    """ViewSet for managing Department objects.
    This viewset provides `list`, `create`, actions for Department objects."""

    queryset = Department.objects.all()
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    

    filterset_class = DepartmentFilter
    

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DepartmentWriteSerializer
        return DepartmentSerializer

class DepartmentListViewSet(viewsets.ReadOnlyModelViewSet):

    """Returns a flat list of department objects"""

    queryset = Department.objects.all()
    lookup_field = 'public_id'

    filter_backends = [SearchFilter]
    search_fields = ['name']
    pagination_class = None 

    serializer_class = DepartmentListSerializer

    

   


class DepartmentUsersViewSet(viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of users in a given department"""
    serializer_class = DepartmentUserLightSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = DepartmentUserFilter
    
    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(
                room__location__department__public_id=department_id
            )
            .select_related(
                'user',
                'room',
                'room__location',
                'room__location__department'
            )
        )
    
class DepartmentUsersMiniViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lightweight, read-only version for dashboard:
    last 20 users of a department, ordered by most recent (-id).
    Pagination disabled.
    """
    serializer_class = DepartmentUserLightSerializer
    pagination_class = None  # disables global pagination

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            UserLocation.objects.filter(
                room__location__department__public_id=department_id
            )
            .select_related(
                'user',
                'room',
                'room__location',
                'room__location__department'
            )
            .order_by('-id')[:20]  # last 20 entries, most recent first
        )

class DepartmentLocationsViewSet(viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    serializer_class = DepartmentLocationsLightSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    filterset_class = LocationFilter
    exclude_filter_fields = ["department"]

    lookup_field = 'public_id'


    def get_queryset(self):
        department_id = self.kwargs.get("public_id")

        return (
            Location.objects
            .filter(department__public_id=department_id)
            .annotate(room_count=Count('rooms'))  
            
        )
    
    def get_filterset(self, *args, **kwargs):
        filterset = super().get_filterset(*args, **kwargs)
        filterset.filters.pop("department", None)
        return filterset

class DepartmentLocationsMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentLocationsLightSerializer
    lookup_field = 'public_id'
    pagination_class = None  # disable global pagination

    def get_queryset(self):
        department_id = self.kwargs.get("public_id")
        return (
            Location.objects.filter(department__public_id=department_id)
            .annotate(room_count=Count('rooms'))
            .order_by('-id')[:20]  # last 20 locations
        )


class DepartmentEquipmentViewSet(viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    """Retrieves a list of equipment in a given department"""
    serializer_class = DepartmentEquipmentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department"]

    filterset_class = EquipmentFilter

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__location__department__public_id=department_id)
    


class DepartmentEquipmentMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentEquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Equipment.objects.filter(room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )


class DepartmentConsumablesViewSet(viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    """Retrieves a list of consumables in a given department"""
    serializer_class = DepartmentConsumableSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department"]

    filterset_class = ConsumableFilter

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__location__department__public_id=department_id)
    


class DepartmentConsumablesMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentConsumableSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Consumable.objects.filter(room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )

class DepartmentAccessoriesViewSet(ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of accessories in a given department"""
    serializer_class = DepartmentAccessorySerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

 
    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__location__department__public_id=department_id)
    

class DepartmentAccessoriesMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentAccessorySerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Accessory.objects.filter(room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )    

class DepartmentComponentsViewSet(ExcludeFiltersMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of components in a given department"""
    serializer_class = DepartmentComponentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department"]


    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__location__department__public_id=department_id)
    
    

class DepartmentComponentsMiniViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentComponentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Component.objects.filter(equipment__room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )
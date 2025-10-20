from django.shortcuts import render
from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from ..models import Consumable, User, Department, Location, Equipment, Component, Accessory, UserLocation, Room
from ..serializers import *
from ..serializers.roles import RoleReadSerializer
from django.views.generic.detail import SingleObjectMixin
from rest_framework.generics import ListAPIView
from ..filters import *
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count  
from ..utils import ExcludeFiltersMixin
from ..mixins import ScopeFilterMixin
from ..permissions import DepartmentPermission
from ..pagination import  FlexiblePagination
from django.db.models import Q

class DepartmentModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):

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

    permission_classes=[DepartmentPermission]


    filterset_class = AreaUserFilter

    pagination_class = FlexiblePagination

    
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
            ).order_by('-id')
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

    permission_classes=[DepartmentPermission]

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

class DepartmentLocationsViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet, ExcludeFiltersMixin):
    serializer_class = DepartmentLocationsLightSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]

    search_fields = ['name']
    filterset_class = LocationFilter
    exclude_filter_fields = ["department"]

    permission_classes=[DepartmentPermission]

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
    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

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

    permission_classes=[DepartmentPermission]

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        return (
            Component.objects.filter(equipment__room__location__department__public_id=department_id)
            .order_by('-id')[:20]
        )
    

class DepartmentRolesViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Retrieves a list of users and thier roles in a given department"""
    serializer_class = RoleReadSerializer
    lookup_field = 'public_id'

    permission_classes=[DepartmentPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['role']

    # filterset_class = RoleFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        department_id = self.kwargs.get('public_id')
        
        return RoleAssignment.objects.filter(
            Q(department__public_id=department_id) |
            Q(location__department__public_id=department_id) |
            Q(room__location__department__public_id=department_id)
        ).order_by('-id')
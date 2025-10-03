from rest_framework import viewsets
from ..serializers.rooms import  *
from ..models import Room, Equipment, Consumable,Accessory,Component,UserLocation
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from ..filters import ComponentFilter, EquipmentFilter, ConsumableFilter,AccessoryFilter,RoomFilter, UserLocationFilter
from ..utils import ExcludeFiltersMixin
from ..permissions import *
from ..mixins import ScopeFilterMixin
from django.db.models import Case, When, Value, IntegerField
from ..pagination import FlexiblePagination
from ..serializers import *

class RoomModelViewSet(ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Room objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Room objects."""
        
    queryset = Room.objects.all().order_by("id")
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    pagination_class = FlexiblePagination

    filterset_class = RoomFilter


    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoomWriteSerializer
        return RoomReadSerializer
    

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
    

        
class RoomListViewset(ScopeFilterMixin, viewsets.ModelViewSet):
   
    queryset = Room.objects.all()
    lookup_field = 'public_id'
    pagination_class = None

    filter_backends = [SearchFilter]
    search_fields = ['name']

    serializer_class = RoomListSerializer

    
class RoomUsersViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of users in a given room"""
    serializer_class = RoomUserLightSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend]
    filterset_class = UserLocationFilter

    pagination_class = FlexiblePagination


    exclude_filter_fields = ["department", "location", "room"]
    


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
        

class RoomEquipmentViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of equipment in a given room"""
    serializer_class = EquipmentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = EquipmentFilter

    pagination_class = FlexiblePagination


    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__public_id=room_id)
    
    def get_serializer(self, *args, **kwargs):
        # Exclude department fields for this department-level view
        kwargs['exclude_department'] = True
        kwargs['exclude_location'] = True
        kwargs['exclude_room'] = True
        return super().get_serializer(*args, **kwargs)
    

class RoomConsumablesViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of consumables in a given room"""
    serializer_class = RoomConsumableSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = ConsumableFilter

    pagination_class = FlexiblePagination


    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__public_id=room_id)
    

class RoomAccessoriesViewSet(ScopeFilterMixin, ExcludeFiltersMixin, viewsets.ModelViewSet):
    """Retrieves a list of accessories in a given room"""
    serializer_class = RoomAccessorySerializer
    lookup_field = 'public_id'

    exclude_filter_fields = ["department", "location", "room"]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    filterset_class = AccessoryFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__public_id=room_id)
    

class RoomComponentsViewSet(ScopeFilterMixin,ExcludeFiltersMixin,viewsets.ModelViewSet):
    """Retrieves a list of components in a given room"""
    serializer_class = RoomComponentSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']

    exclude_filter_fields = ["department", "location", "room"]

    filterset_class = ComponentFilter

    pagination_class = FlexiblePagination

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__public_id=room_id)
    

class RoomComponentsMiniViewSet(ScopeFilterMixin,viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomComponentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Component.objects.filter(equipment__room__public_id=room_id).order_by('-id')[:20]


class RoomUsersMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
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


class RoomEquipmentMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomEquipmentSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Equipment.objects.filter(room__public_id=room_id).order_by('-id')[:20]


class RoomConsumablesMiniViewSet(ScopeFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomConsumableSerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Consumable.objects.filter(room__public_id=room_id).order_by('-id')[:20]


class RoomAccessoriesMiniViewSet(ScopeFilterMixin,viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomAccessorySerializer
    lookup_field = 'public_id'
    pagination_class = None

    def get_queryset(self):
        room_id = self.kwargs.get('public_id')
        return Accessory.objects.filter(room__public_id=room_id).order_by('-id')[:20]


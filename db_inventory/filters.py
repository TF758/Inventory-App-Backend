import django_filters
from .models import *



class EquipmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    brand = django_filters.CharFilter(lookup_expr='icontains')
    model = django_filters.CharFilter(lookup_expr='icontains')
    serial_number = django_filters.CharFilter(lookup_expr='icontains')
    identifier = django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(
        field_name='room__name', lookup_expr='icontains'
    )


    class Meta:
        model = Equipment
        fields = fields = [
        'name',
        'brand',
        'model',
        'serial_number',
        'identifier',
        'room',
       
    ]
        
class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name="department__name")

    class Meta:
        model = Location
        fields = [
            'name',
            'department',
        ]

class RoomFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(lookup_expr='icontains')
    area = django_filters.CharFilter(lookup_expr='icontains')
    section = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name="location__name")
    department =  django_filters.CharFilter(lookup_expr='icontains', field_name="location__department__name")


    class Meta:
        model = Room
        fields = [
            'name',
            'room',
            'area',
            'section',
            'department',
        ]

class ComponentFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    brand=  django_filters.CharFilter(lookup_expr='icontains')
    model=django_filters.CharFilter(lookup_expr='icontains')
    serial_number=django_filters.CharFilter(lookup_expr='icontains')
    identifier = django_filters.CharFilter(lookup_expr='icontains')
    equipment =django_filters.CharFilter(lookup_expr='icontains', field_name="equipment__name")

    class Meta:
        model = Component
        fields = [
            'name',
            'brand',
            'model',
            'serial_number',
            'identifier',
            'equipment',
        ]


class AccessoryFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    serial_number=django_filters.CharFilter(lookup_expr='icontains')
    room_name = django_filters.CharFilter(
        field_name='room__name', lookup_expr='icontains'
    )

    class Meta:
        model = Accessory
        fields = [
            'name',
            'serial_number',
            'room_name',
        ]


class ConsumableFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    room_name = django_filters.CharFilter(
        field_name='room__name', lookup_expr='icontains'
    )

    class Meta:
        model = Consumable
        fields = [
            'name',
            'room_name',
          
        ]

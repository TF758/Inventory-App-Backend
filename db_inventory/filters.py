import django_filters
from .models import *

class DepartmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Department
        fields = [
            'name',
            'description',
        ]

class EquipmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    brand = django_filters.CharFilter(lookup_expr='icontains')
    model = django_filters.CharFilter(lookup_expr='icontains')
    serial_number = django_filters.CharFilter(lookup_expr='icontains')
    identifier = django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.NumberFilter(field_name="room__id")
    location = django_filters.NumberFilter(field_name="room__location__id")
    department = django_filters.NumberFilter(field_name="room__location__department__id")


    class Meta:
        model = Equipment
        fields = [
        'name',
        'brand',
        'model',
        'serial_number',
        'identifier',
        'room',
        'location',
        'department',
       
    ]
        
class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    department = django_filters.NumberFilter(field_name="department__id")

    class Meta:
        model = Location
        fields = [
            'name',
            'department',
        ]

class RoomFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    area = django_filters.CharFilter(lookup_expr='icontains')
    section = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.NumberFilter(field_name="location__id")
    department = django_filters.NumberFilter(field_name="location__department__id")


    class Meta:
        model = Room
        fields = [
            'name',
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
    room = django_filters.NumberFilter(field_name="equipment__room__id")
    location = django_filters.NumberFilter(field_name="equipment__room__location__id")
    department = django_filters.NumberFilter(field_name="equipment__room__location__department__id")

    class Meta:
        model = Component
        fields = [
            'name',
            'brand',
            'model',
            'serial_number',
            'identifier',
            'equipment',
            'room',
            'location',
            'department',
        ]


class AccessoryFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    serial_number=django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.NumberFilter(field_name="room__id")
    location = django_filters.NumberFilter(field_name="room__location__id")
    department = django_filters.NumberFilter(field_name="room__location__department__id")


    class Meta:
        model = Accessory
        fields = [
            'name',
            'serial_number',
            'room',
            'location',
            'department',
        ]


class ConsumableFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.NumberFilter(field_name="room__id")
    location = django_filters.NumberFilter(field_name="room__location__id")
    department = django_filters.NumberFilter(field_name="room__location__department__id")


    class Meta:
        model = Consumable
        fields = [
            'name',
            'room',
            'location',
            'department',
        ]

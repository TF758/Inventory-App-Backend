import django_filters
from .models import User, Department, Location, Equipment, Component, Accessory, UserLocation, Consumable



class EquipmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    brand = django_filters.CharFilter(lookup_expr='icontains')
    model = django_filters.CharFilter(lookup_expr='icontains')
    serial_number = django_filters.CharFilter(lookup_expr='icontains')
    identifier = django_filters.CharFilter(lookup_expr='icontains')
    location_name = django_filters.CharFilter(
        field_name='location__name', lookup_expr='icontains'
    )
    department= django_filters.CharFilter(
    field_name="location__department__name",
    lookup_expr='icontains'
)

    class Meta:
        model = Equipment
        fields = fields = [
        'name',
        'brand',
        'model',
        'serial_number',
        'identifier',
        'location_name',
        'department',
    ]
        
class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(lookup_expr='icontains')
    area = django_filters.CharFilter(lookup_expr='icontains')
    section = django_filters.CharFilter(lookup_expr='icontains')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name="department__name")

    class Meta:
        model = Location
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
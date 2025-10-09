import django_filters
from .models import *
from django.db.models import Case, When, Value, IntegerField, Q

class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr='istartswith')
    fname = django_filters.CharFilter(method='filter_fname')
    lname = django_filters.CharFilter(method='filter_lname')
    is_active = django_filters.BooleanFilter()
    last_login = django_filters.DateFromToRangeFilter()
    date_joined = django_filters.DateFromToRangeFilter()

    class Meta:
        model = User
        fields = [
            'email',
            'fname',
            'lname',
            'is_active',
            'date_joined',
            'last_login',
        ]

    def filter_fname(self, queryset, name, value):
        if value:
            # Start-with first, then contains
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(fname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).filter(
                Q(fname__icontains=value)
            ).order_by('starts_with_order', 'fname')
        return queryset

    def filter_lname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(lname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).filter(
                Q(lname__icontains=value)
            ).order_by('starts_with_order', 'lname')
        return queryset

class DepartmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Department
        fields = [
            'name',
            'description',
        ]

class AreaUserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(
        lookup_expr='istartswith',
        field_name='user__email'
    )
    fname = django_filters.CharFilter(method='filter_fname')
    lname = django_filters.CharFilter(method='filter_lname')
    room = django_filters.CharFilter(
        lookup_expr='icontains',
        field_name='room__public_id'
    )
    location = django_filters.CharFilter(
        lookup_expr='icontains',
        field_name='room__location__public_id'
    )
    department = django_filters.CharFilter(
        lookup_expr='icontains',
        field_name='room__location__department__public_id'
    )

    class Meta:
        model = UserLocation
        fields = [
            'user',
            'email',
            'fname',
            'lname',
            'room',
            'location',
            'department',
        ]

    def filter_fname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(user__fname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).filter(
                Q(user__fname__icontains=value)
            ).order_by('starts_with_order', 'user__fname')
        return queryset

    def filter_lname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(user__lname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).filter(
                Q(user__lname__icontains=value)
            ).order_by('starts_with_order', 'user__lname')
        return queryset


class EquipmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    brand = django_filters.CharFilter(lookup_expr='icontains')
    model = django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='room__public_id')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__department__public_id')



    class Meta:
        model = Equipment
        fields = [
        'name',
        'brand',
        'model',
        'room',
        'location',
        'department',
       
    ]
        
class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains', field_name="name")
    department = django_filters.CharFilter(lookup_expr='exact', field_name="department__public_id")
    location = django_filters.CharFilter(field_name='public_id', lookup_expr='exact')  

    class Meta:
        model = Location
        fields = [
            'name',
            'department',
            'location'
        ]

class RoomFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(field_name='location__public_id', lookup_expr='exact')
    department = django_filters.CharFilter(field_name='location__department__public_id', lookup_expr='exact')
    room = django_filters.CharFilter(field_name='public_id', lookup_expr='exact')  


    class Meta:
        model = Room
        fields = [
            'name',
            'location',
            'department',
            'room',
        ]

class ComponentFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    brand=  django_filters.CharFilter(lookup_expr='icontains')
    model=django_filters.CharFilter(lookup_expr='icontains')
    equipment =django_filters.CharFilter(lookup_expr='icontains', field_name="equipment__name")
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='equipment__room__public_id')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='equipment__room__location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='equipment__room__location__department__public_id')


    class Meta:
        model = Component
        fields = [
            'name',
            'brand',
            'model',
            'equipment',
            'room',
            'location',
            'department',
        ]


class AccessoryFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    serial_number=django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='room__public_id')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__department__public_id')



    class Meta:
        model = Accessory
        fields = [
            'name',
            'room',
            'location',
            'department',
        ]


class ConsumableFilter(django_filters.FilterSet):
    name= django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='room__public_id')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__department__public_id')



    class Meta:
        model = Consumable
        fields = [
            'name',
            'room',
            'location',
            'department',
        ]

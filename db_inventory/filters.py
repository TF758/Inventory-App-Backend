import django_filters
from .models import *

class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr= 'istartswith')
    fname = django_filters.CharFilter(lookup_expr='icontains')
    lname = django_filters.CharFilter(lookup_expr='icontains')
    # is_active = django_filters.BooleanFilter()
    last_login = django_filters.DateFromToRangeFilter()
    date_joined = django_filters.DateFromToRangeFilter()

    class Meta:
        model = User
        fields = [
            'email',
            'fname',
            'lname',
            # 'is_active',
            'date_joined',
            'last_login',
        ]


class DepartmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Department
        fields = [
            'name',
            'description',
        ]

class DepartmentUserFilter(django_filters.FilterSet):
    user_email = django_filters.CharFilter(lookup_expr='istartswith', field_name='user__email')
    user_fname = django_filters.CharFilter(lookup_expr='icontains', field_name='user__fname')
    user_lname = django_filters.CharFilter(lookup_expr='icontains', field_name='user__lname')
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='room__name')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__name')
  


    class Meta:
        model = UserLocation
        fields = [
            'user_id',
            'user_email',
            'user_fname',
            'user_lname',
            'room',
            'location',     
        ]

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
    department = django_filters.CharFilter(lookup_expr='icontains', field_name="department__name")

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
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='location__department__public_id')


    class Meta:
        model = Room
        fields = [
            'name',
            'area',
            'section',
            'location',
            'department',
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

class UserLocationFilter (django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr='icontains', field_name="user__email")
    fname = django_filters.CharFilter(lookup_expr='icontains', field_name="user__fname")
    lname = django_filters.CharFilter(lookup_expr='icontains', field_name="user__lname")
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='room__public_id')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__department__public_id')

    class Meta:
        models= UserLocation
        fields = [
            'email',
            'fname',
            'lname',
            'room',
            'location',
            'department',
        ]
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


class UserLocationFilter(django_filters.FilterSet):
    """
    Filters for UserLocation based on related public_ids and user info.
    """

    # --- Filter by public IDs ---
    user_id = django_filters.CharFilter(
        field_name="user__public_id", lookup_expr="iexact", label="User Public ID"
    )
    room_id = django_filters.CharFilter(
        field_name="room__public_id", lookup_expr="iexact", label="Room Public ID"
    )
    location_id = django_filters.CharFilter(
        field_name="room__location__public_id", lookup_expr="iexact", label="Location Public ID"
    )
    department_id = django_filters.CharFilter(
        field_name="room__location__department__public_id", lookup_expr="iexact", label="Department Public ID"
    )

    # --- Filter by user info ---
    email = django_filters.CharFilter(
        field_name="user__email", lookup_expr="icontains", label="User Email"
    )
    fname = django_filters.CharFilter(
        field_name="user__fname", lookup_expr="icontains", label="First Name"
    )
    lname = django_filters.CharFilter(
        field_name="user__lname", lookup_expr="icontains", label="Last Name"
    )
    job_title = django_filters.CharFilter(
        field_name="user__job_title", lookup_expr="icontains", label="Job Title"
    )

    class Meta:
        model = UserLocation
        fields = [
            "user_id",
            "room_id",
            "location_id",
            "department_id",
            "email",
            "fname",
            "lname",
            "job_title",
        ]

class RoleAssignmentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_user_search")
    role = django_filters.CharFilter(field_name="role", lookup_expr="iexact")
    area_type = django_filters.CharFilter(method="filter_area_type")

    def filter_user_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            Q(user__fname__icontains=value)
            | Q(user__lname__icontains=value)
            | Q(user__email__icontains=value)
        )

    def filter_area_type(self, queryset, name, value):
        value = value.lower()
        if value == "department":
            return queryset.filter(department__isnull=False)
        elif value == "location":
            return queryset.filter(location__isnull=False)
        elif value == "room":
            return queryset.filter(room__isnull=False)
        return queryset.none()  # if invalid area_type

    class Meta:
        model = RoleAssignment
        fields = ["role", "area_type", "search"]

class AuditLogFilter(django_filters.FilterSet):
    # Filter by email directly
    user_email = django_filters.CharFilter(field_name="user_email", lookup_expr="icontains")
    
    # Filter by other fields as before
    event_type = django_filters.CharFilter(field_name="event_type", lookup_expr="iexact")
    target_model = django_filters.CharFilter(field_name="target_model", lookup_expr="icontains")
    department = django_filters.CharFilter(field_name="department__public_id", lookup_expr="iexact")
    location = django_filters.CharFilter(field_name="location__public_id", lookup_expr="iexact")
    room = django_filters.CharFilter(field_name="room__public_id", lookup_expr="iexact")
    created_at_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = [
            "user_email",
            "event_type",
            "target_model",
            "department",
            "location",
            "room",
            "created_at_after",
            "created_at_before",
        ]
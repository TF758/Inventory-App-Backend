import django_filters
from db_inventory.models import *
from django.db.models import Case, When, Value, IntegerField, Q, Sum, F, Value
from django.db.models.functions import Coalesce
from db_inventory.utils.filters import BaseAssetNameFilter

class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr="istartswith")
    fname = django_filters.CharFilter(method="filter_fname")
    lname = django_filters.CharFilter(method="filter_lname")
    is_active = django_filters.BooleanFilter()
    last_login = django_filters.DateFromToRangeFilter()
    date_joined = django_filters.DateFromToRangeFilter()

    # for autho complete querying
    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = User
        fields = [
            "email",
            "fname",
            "lname",
            "is_active",
            "date_joined",
            "last_login",
            "q",
        ]


    def filter_fname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(fname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).filter(fname__icontains=value).order_by(
                "starts_with_order", "fname"
            )
        return queryset

    def filter_lname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(lname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).filter(lname__icontains=value).order_by(
                "starts_with_order", "lname"
            )
        return queryset


    def filter_q(self, queryset, name, value):
        """
        used primarily for live search by email
        """

        value = value.strip().lower()
        if len(value) < 2:
            return queryset.none()

        return (
            queryset
            .filter(email__istartswith=value)
            .order_by("email")[:20]
        )


class DepartmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = Department
        fields = [
            'name',
            'description',
        ]
    def filter_q(self, queryset, name, value):
        """
        used primarily for live search by name
        """

        value = value.strip().lower()
        if len(value) < 2:
            return queryset.none()

        return (
            queryset
            .filter(name__istartswith=value)
            .order_by("name")[:20]
        )

class AreaUserFilter(django_filters.FilterSet):
    """
    Filter for scoped user lookup.
    """
    email = django_filters.CharFilter(lookup_expr="istartswith",field_name="user__email")
    fname = django_filters.CharFilter(method="filter_fname")
    lname = django_filters.CharFilter(method="filter_lname")
    room = django_filters.CharFilter(lookup_expr="iexact",field_name="room__public_id")
    location = django_filters.CharFilter(lookup_expr="iexact",field_name="room__location__public_id")
    department = django_filters.CharFilter(lookup_expr="iexact",field_name="room__location__department__public_id")

    # for live searching
    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = UserLocation
        fields = [
            "user",
            "email",
            "fname",
            "lname",
            "room",
            "location",
            "department",
            "q",
        ]


    def filter_fname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(user__fname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).filter(
                user__fname__icontains=value
            ).order_by("starts_with_order", "user__fname")
        return queryset

    def filter_lname(self, queryset, name, value):
        if value:
            queryset = queryset.annotate(
                starts_with_order=Case(
                    When(user__lname__istartswith=value, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).filter(
                user__lname__icontains=value
            ).order_by("starts_with_order", "user__lname")
        return queryset


    def filter_q(self, queryset, name, value):
        """
         used primarily for live search by email
        """

        value = value.strip().lower()
        if len(value) < 2:
            return queryset.none()

        return (
            queryset
            .filter(user__email__istartswith=value)
            .order_by("user__email")[:20]
    )

class EquipmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    brand = django_filters.CharFilter(lookup_expr='icontains')
    model = django_filters.CharFilter(lookup_expr='icontains')
    room = django_filters.CharFilter(lookup_expr='icontains', field_name='room__public_id')
    location = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__public_id')
    department = django_filters.CharFilter(lookup_expr='icontains', field_name='room__location__department__public_id')
    status = django_filters.BaseInFilter(field_name="status",lookup_expr="in")
    is_assigned = django_filters.BooleanFilter(method="filter_is_assigned")


    class Meta:
        model = Equipment
        fields = [
        'name',
        'brand',
        'model',
        'room',
        'location',
        'department',
        'status',
         'is_assigned',
       
    ]
    # filter using equipment asignemnt related_name
    def filter_is_assigned(self, queryset, name, value):
        if value is True:
            # Assigned equipment ONLY
            return queryset.filter(
                active_assignment__isnull=False,
                active_assignment__returned_at__isnull=True,
            )

        if value is False:
            # Unassigned equipment ONLY
            return queryset.exclude(
                active_assignment__isnull=False,
                active_assignment__returned_at__isnull=True,
            )

        return queryset
        
import django_filters
from django.db.models import Q

class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter( lookup_expr="icontains", field_name="name" )
    department = django_filters.CharFilter( lookup_expr="exact", field_name="department__public_id" )
    location = django_filters.CharFilter( field_name="public_id", lookup_expr="exact" )

    q = django_filters.CharFilter(method="filter_q")

    unassigned = django_filters.BooleanFilter( field_name="department", lookup_expr="isnull" )

    class Meta:
        model = Location
        fields = [
            "name",
            "department",
            "location",
            "unassigned",
            "q",
        ]

    def filter_q(self, queryset, name, value):
        """
        Live search for locations
        """
        value = value.strip().lower()

        if len(value) < 2:
            return queryset.none()

        return (
            queryset.filter(
                Q(name__istartswith=value) |
                Q(public_id__istartswith=value)
            )
            .order_by("name")[:20]
        )

class RoomFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_q")
    name = django_filters.CharFilter(lookup_expr="icontains")

    location = django_filters.CharFilter(
        field_name="location__public_id", lookup_expr="exact"
    )

    department = django_filters.CharFilter(
        field_name="location__department__public_id", lookup_expr="exact"
    )

    room = django_filters.CharFilter(
        field_name="public_id", lookup_expr="exact"
    )

    unassigned = django_filters.BooleanFilter(method="filter_unassigned")

    class Meta:
        model = Room
        fields = [
            "name",
            "location",
            "department",
            "room",
            "unassigned",
        ]

    def filter_unassigned(self, queryset, name, value):
        """
        Return rooms without a location (orphans)
        """
        if value:
            return queryset.filter(location__isnull=True)
        return queryset

    def filter_q(self, queryset, name, value):
        """
        Live search for rooms
        """
        value = value.strip().lower()
        if len(value) < 2:
            return queryset.none()

        return (
            queryset.filter(
                Q(name__istartswith=value) |
                Q(public_id__istartswith=value)
            )
            .order_by("name")[:20]
        )

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
    name = django_filters.CharFilter(lookup_expr="icontains")
    serial_number = django_filters.CharFilter(lookup_expr="icontains")

    room = django_filters.CharFilter(field_name="room__public_id", lookup_expr="icontains")
    location = django_filters.CharFilter(field_name="room__location__public_id", lookup_expr="icontains")
    department = django_filters.CharFilter(field_name="room__location__department__public_id", lookup_expr="icontains")

    quantity = django_filters.NumberFilter(field_name="quantity")
    quantity_min = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")
    quantity_max = django_filters.NumberFilter(field_name="quantity", lookup_expr="lte")

    available_quantity_min = django_filters.NumberFilter(method="filter_available_min")
    available_quantity_max = django_filters.NumberFilter(method="filter_available_max")

    out_of_stock = django_filters.BooleanFilter(method="filter_out_of_stock")

    class Meta:
        model = Accessory
        fields = [
            "name",
            "serial_number",
            "room",
            "location",
            "department",
            "quantity",
            "quantity_min",
            "quantity_max",
        ]

    def with_available_quantity(self, queryset):
        return queryset.annotate(
            assigned_qty=Coalesce(
                Sum("assignments__quantity", filter=models.Q(assignments__returned_at__isnull=True)),
                Value(0),
            ),
            available_qty=F("quantity") - F("assigned_qty"),
        )

    def filter_available_min(self, queryset, name, value):
        queryset = self.with_available_quantity(queryset)
        return queryset.filter(available_qty__gte=value)

    def filter_available_max(self, queryset, name, value):
        queryset = self.with_available_quantity(queryset)
        return queryset.filter(available_qty__lte=value)

    def filter_out_of_stock(self, queryset, name, value):
        if value:
            return queryset.filter(available_qty__lte=0)
        return queryset
class ConsumableFilter(django_filters.FilterSet):

    name = django_filters.CharFilter(lookup_expr='icontains')

    room = django_filters.CharFilter(field_name='room__public_id', lookup_expr='icontains')
    location = django_filters.CharFilter(field_name='room__location__public_id', lookup_expr='icontains')
    department = django_filters.CharFilter(field_name='room__location__department__public_id', lookup_expr='icontains')

    quantity = django_filters.NumberFilter(field_name="quantity")
    quantity_min = django_filters.NumberFilter(field_name="quantity", lookup_expr="gte")
    quantity_max = django_filters.NumberFilter(field_name="quantity", lookup_expr="lte")

    low_stock = django_filters.BooleanFilter(method="filter_low_stock")
    out_of_stock = django_filters.BooleanFilter(method="filter_out_of_stock")

    class Meta:
        model = Consumable
        fields = [
            "name",
            "room",
            "location",
            "department",
            "quantity",
            "quantity_min",
            "quantity_max",
            "low_stock",
            "out_of_stock",
        ]

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(
                low_stock_threshold__gt=0,
                quantity__gt=0,
                quantity__lte=F("low_stock_threshold"),
            )
        return queryset

    def filter_out_of_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity=0)
        return queryset


class UserLocationFilter(django_filters.FilterSet):
    """
    Filters for UserLocation based on related public_ids and user info.
    """

    user_id = django_filters.CharFilter(field_name="user__public_id", lookup_expr="iexact")
    room_id = django_filters.CharFilter(field_name="room__public_id", lookup_expr="iexact")
    location_id = django_filters.CharFilter(field_name="room__location__public_id", lookup_expr="iexact")
    department_id = django_filters.CharFilter(field_name="room__location__department__public_id")

    # --- Filter by user info ---
    email = django_filters.CharFilter(field_name="user__email", lookup_expr="icontains")
    fname = django_filters.CharFilter(field_name="user__fname", lookup_expr="icontains")
    lname = django_filters.CharFilter( field_name="user__lname", lookup_expr="icontains")
    job_title = django_filters.CharFilter(field_name="user__job_title", lookup_expr="icontains")

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
    role_group = django_filters.CharFilter(method="filter_role_group")

    area_type = django_filters.CharFilter(method="filter_area_type")

    department = django_filters.CharFilter(field_name="department__public_id")
    location = django_filters.CharFilter(field_name="location__public_id")
    room = django_filters.CharFilter(field_name="room__public_id")

    assigned_by = django_filters.CharFilter(field_name="assigned_by__public_id")

    assigned_after = django_filters.DateTimeFilter(field_name="assigned_date", lookup_expr="gte")
    assigned_before = django_filters.DateTimeFilter(field_name="assigned_date", lookup_expr="lte")

    class Meta:
        model = RoleAssignment
        fields = [
            "search",
            "role",
            "role_group",
            "area_type",
            "department",
            "location",
            "room",
            "assigned_by",
        ]

    # -----------------------------
    # User Search
    # -----------------------------
    def filter_user_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            Q(user__fname__icontains=value)
            | Q(user__lname__icontains=value)
            | Q(user__email__icontains=value)
        )

    # -----------------------------
    # Area Type Filter
    # -----------------------------
    def filter_area_type(self, queryset, name, value):
        value = value.lower()

        if value == "department":
            return queryset.filter(department__isnull=False)

        if value == "location":
            return queryset.filter(location__isnull=False)

        if value == "room":
            return queryset.filter(room__isnull=False)

        if value == "site":
            return queryset.filter(role="SITE_ADMIN")

        return queryset

    # -----------------------------
    # Role Group Filter
    # -----------------------------
    def filter_role_group(self, queryset, name, value):
        value = value.upper()

        if value == "ROOM":
            return queryset.filter(role__startswith="ROOM")

        if value == "LOCATION":
            return queryset.filter(role__startswith="LOCATION")

        if value == "DEPARTMENT":
            return queryset.filter(role__startswith="DEPARTMENT")

        if value == "SITE":
            return queryset.filter(role="SITE_ADMIN")

        return queryset

class AuditLogFilter(django_filters.FilterSet):

    user_email = django_filters.CharFilter(field_name="user_email", lookup_expr="icontains")
    

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


class EquipmentAssignmentFilter(django_filters.FilterSet):
    equipment = django_filters.CharFilter(field_name="equipment__name",lookup_expr="icontains",)
    room = django_filters.CharFilter(field_name="equipment__room__public_id",lookup_expr="exact",)
    location = django_filters.CharFilter(field_name="equipment__room__location__public_id",lookup_expr="exact",)
    department = django_filters.CharFilter(field_name="equipment__room__location__department__public_id",lookup_expr="exact",)

    class Meta:
        model = EquipmentAssignment
        fields = [
            "equipment",
            "room",
            "location",
            "department",
        ]



class SiteNameChangeHistoryFilter(django_filters.FilterSet):
    site_type = django_filters.CharFilter(field_name="site_type")
    object_public_id = django_filters.CharFilter(field_name="object_public_id")
    user_email = django_filters.CharFilter(field_name="user_email", lookup_expr="iexact")

    start_date = django_filters.DateTimeFilter(
        field_name="changed_at", lookup_expr="gte"
    )
    end_date = django_filters.DateTimeFilter(
        field_name="changed_at", lookup_expr="lte"
    )

    class Meta:
        model = SiteNameChangeHistory
        fields = [
            "site_type",
            "object_public_id",
            "user_email",
        ]

class SelfEquipmentFilter(BaseAssetNameFilter):
    name_field = "equipment__name"

    class Meta:
        model = EquipmentAssignment
        fields = ["name"]

class SelfAccessoryFilter(BaseAssetNameFilter):
    name_field = "accessory__name"

    class Meta:
        model = AccessoryAssignment
        fields = ["name"]

class SelfConsumableFilter(BaseAssetNameFilter):
    name_field = "consumable__name"

    class Meta:
        model = ConsumableIssue
        fields = ["name"]
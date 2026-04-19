import django_filters
from django.db.models import Case, When, Value, IntegerField, Q, Sum, F, Value
from sites.models.sites import Department, Location, UserPlacement, Room


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
        model = UserPlacement
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

class UserPlacementFilter(django_filters.FilterSet):
    """
    Filters for UserPlacement based on related public_ids and user info.
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
        model = UserPlacement
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

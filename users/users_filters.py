import django_filters
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField, Q, Sum, F, Value
from users.models.users import User


class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr="istartswith")
    fname = django_filters.CharFilter(method="filter_fname")
    lname = django_filters.CharFilter(method="filter_lname")

    is_active = django_filters.BooleanFilter()
    is_system_user = django_filters.BooleanFilter()
    is_locked = django_filters.BooleanFilter()

    is_actually_locked = django_filters.BooleanFilter( method="filter_is_actually_locked" )

    last_login = django_filters.DateFromToRangeFilter()
    date_joined = django_filters.DateFromToRangeFilter()

    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = User
        fields = [
            "email",
            "fname",
            "lname",
            "is_active",
            "is_system_user",
            "is_locked",
            "is_actually_locked",
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
    

    def filter_is_actually_locked(
        self,
        queryset,
        name,
        value,
    ):

        now = timezone.now()

        locked_q = (
            Q(is_locked=True)
            | Q(locked_until__gt=now)
        )

        if value:
            return queryset.filter(locked_q)

        return queryset.exclude(locked_q)


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

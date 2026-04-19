import django_filters
from core.models.audit import AuditLog, SiteNameChangeHistory
from core.models.sessions import UserSession



class AuditLogFilter(django_filters.FilterSet):

    user_email = django_filters.CharFilter(field_name="user_email", lookup_expr="icontains")
    

    event_type = django_filters.CharFilter(field_name="event_type", lookup_expr="iexact")
    target_model = django_filters.CharFilter(field_name="target_model", lookup_expr="icontains")
    department = django_filters.CharFilter(field_name="department__public_id", lookup_expr="iexact")
    location = django_filters.CharFilter(field_name="location__public_id", lookup_expr="iexact")
    room = django_filters.CharFilter(field_name="room__public_id", lookup_expr="iexact")
    created_at_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    exclude_noise = django_filters.BooleanFilter(method="filter_exclude_noise")

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

    def filter_exclude_noise(self, queryset, name, value):
        if value:
            return queryset.exclude(event_type__in=AuditLog.Events.NOISE_EVENTS)
        return queryset



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


class UserSessionFilter(django_filters.FilterSet):

    user_email = django_filters.CharFilter( field_name="user__email", lookup_expr="icontains", )

    status = django_filters.ChoiceFilter( choices=UserSession.Status.choices )

    device_name = django_filters.CharFilter( field_name="device_name", lookup_expr="icontains", )
    ip_address = django_filters.CharFilter( field_name="ip_address", lookup_expr="icontains", )

    created_after = django_filters.DateTimeFilter( field_name="created_at", lookup_expr="gte", )

    created_before = django_filters.DateTimeFilter( field_name="created_at", lookup_expr="lte", )

    class Meta:
        model = UserSession
        fields = [
            "status",
            "device_name",
            "ip_address",
            "user_email",
        ]
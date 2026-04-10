import django_filters

from inventory_metrics.models.reports import ReportJob




class ReportJobFilter(django_filters.FilterSet):

    created_after = django_filters.IsoDateTimeFilter( field_name="created_at", lookup_expr="gte", )

    created_before = django_filters.IsoDateTimeFilter( field_name="created_at", lookup_expr="lte", )

    class Meta:
        model = ReportJob
        fields = [
            "status",
            "report_type",
            "created_after",
            "created_before",
        ]
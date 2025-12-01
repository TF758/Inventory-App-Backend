from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils.dateparse import parse_date

class TimeSeriesViewset(ReadOnlyModelViewSet):
    """Base class for returning date-based metrics suitable for graphs."""

    date_field = "date"  # override in child classes

    def filter_queryset_by_date(self, qs):
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")

        if start:
            qs = qs.filter(**{f"{self.date_field}__gte": parse_date(start)})
        if end:
            qs = qs.filter(**{f"{self.date_field}__lte": parse_date(end)})

        return qs.order_by(self.date_field)

    @action(detail=False, methods=["get"])
    def timeseries(self, request):
        """Return all numeric fields as arrays for chart rendering."""
        qs = self.filter_queryset_by_date(self.get_queryset())

        if not qs.exists():
            return Response({"labels": [], "data": {} })

        labels = [getattr(i, self.date_field).isoformat() for i in qs]

        # Include only integer fields
        fields = [
            f.name for f in qs.model._meta.get_fields()
            if f.get_internal_type() in ("IntegerField", "PositiveIntegerField")
        ]

        data = {field: [getattr(i, field) for i in qs] for field in fields}

        return Response({
            "labels": labels,
            "data": data
        })

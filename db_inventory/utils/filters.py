import django_filters


class BaseAssetNameFilter(django_filters.FilterSet):
    """
    Generic filter for asset-like models that exposes a `name` search.
    Subclasses must define `name_field`.
    """

    name = django_filters.CharFilter(method="filter_name")

    name_field: str = None  # must be overridden

    def filter_name(self, queryset, name, value):
        if not self.name_field:
            return queryset
        return queryset.filter(**{f"{self.name_field}__istartswith": value})
"""DRF filtering helpers."""

from __future__ import annotations


class ExcludeFiltersMixin:
    """Remove selected fields from a view's filterset at runtime and in schema."""

    exclude_filter_fields: list[str] = []

    def get_filterset_class(self):
        base_class = super().get_filterset_class()
        exclude = set(self.exclude_filter_fields)

        class DynamicFilterset(base_class):
            class Meta(base_class.Meta):
                fields = {
                    name: lookups
                    for name, lookups in base_class.Meta.fields.items()
                    if name not in exclude
                }

        return DynamicFilterset

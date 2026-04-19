from django.db import models
import django_filters
from django.db.models import Case, When, Value, IntegerField, Q, Sum, F, Value
from django.db.models.functions import Coalesce
from assets.models.assets import Accessory, Component, Consumable, Equipment



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
        if "available_qty" in queryset.query.annotations:
            return queryset

        return queryset.annotate(
            assigned_qty=Coalesce(
                Sum(
                    "assignments__quantity",
                    filter=models.Q(assignments__returned_at__isnull=True),
                ),
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
        if not value:
            return queryset

        queryset = self.with_available_quantity(queryset)
        return queryset.filter(available_qty__lte=0)

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

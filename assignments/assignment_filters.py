import django_filters
from core.utils.filters import BaseAssetNameFilter

from assignments.models.asset_assignment import EquipmentAssignment, AccessoryAssignment, ConsumableIssue, ReturnRequest, ReturnRequestItem


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

class ReturnRequestFilter(django_filters.FilterSet):

    status = django_filters.CharFilter(field_name="status")
    asset_type = django_filters.CharFilter( field_name="items__item_type", lookup_expr="exact" )
    requested_after = django_filters.DateTimeFilter( field_name="requested_at", lookup_expr="gte" )
    requested_before = django_filters.DateTimeFilter( field_name="requested_at", lookup_expr="lte" )
    processed_after = django_filters.DateTimeFilter( field_name="processed_at", lookup_expr="gte" )
    processed_before = django_filters.DateTimeFilter( field_name="processed_at", lookup_expr="lte" )

    class Meta:
        model = ReturnRequest
        fields = [
            "status",
            "asset_type",
        ]

class AdminReturnRequestFilter(django_filters.FilterSet):

    # ------------------------
    # Core filters
    # ------------------------
    status = django_filters.ChoiceFilter(
        field_name="status", choices=ReturnRequest.Status.choices )
    asset_type = django_filters.CharFilter( field_name="items__item_type" )
    requester = django_filters.CharFilter( field_name="requester__public_id" )
    requested_after = django_filters.DateTimeFilter( field_name="requested_at", lookup_expr="gte" )
    requested_before = django_filters.DateTimeFilter( field_name="requested_at", lookup_expr="lte" )

    # ------------------------
    # Item location filters
    # ------------------------
    department = django_filters.CharFilter(method="filter_department")
    location = django_filters.CharFilter(method="filter_location")
    room = django_filters.CharFilter(method="filter_room")

    # ------------------------
    # Requester location filters (NEW)
    # ------------------------
    requester_department = django_filters.CharFilter( method="filter_requester_department" )
    requester_location = django_filters.CharFilter( method="filter_requester_location" )
    requester_room = django_filters.CharFilter( method="filter_requester_room" )

    class Meta:
        model = ReturnRequest
        fields = [
            "status",
            "asset_type",
            "requester",
            "department",
            "location",
            "room",
            "requester_department",
            "requester_location",
            "requester_room",
        ]

    # ------------------------
    # Item-based filters
    # ------------------------
    def filter_department(self, queryset, name, value):
        return queryset.filter( items__room__location__department__public_id=value ).distinct()

    def filter_location(self, queryset, name, value):
        return queryset.filter( items__room__location__public_id=value ).distinct()

    def filter_room(self, queryset, name, value):
        return queryset.filter( items__room__public_id=value ).distinct()

    # ------------------------
    # Requester-based filters (IMPORTANT)
    # ------------------------
    def filter_requester_department(self, queryset, name, value):
        return queryset.filter(
            requester__user_placements__is_current=True,
            requester__user_placements__room__location__department__public_id=value
        ).distinct()

    def filter_requester_location(self, queryset, name, value):
        return queryset.filter(
            requester__user_placements__is_current=True,
            requester__user_placements__room__location__public_id=value
        ).distinct()

    def filter_requester_room(self, queryset, name, value):
        return queryset.filter(
            requester__user_placements__is_current=True,
            requester__user_placements__room__public_id=value
        ).distinct()
    

class MixAssetFilter:
    """
    Filter class for unified asset list (list of dicts).
    Mimics django_filters style but works on in-memory data.
    """

    def __init__(self, params, queryset):
        self.params = params
        self.queryset = queryset

    def filter(self):
        data = self.queryset

        data = self.filter_type(data)
        data = self.filter_search(data)
        data = self.filter_room(data)
        data = self.filter_can_return(data)
        data = self.filter_pending(data)

        return data

    def filter_type(self, data):
        types = self.params.getlist("asset_type")

        if not types:
            return data

        return [x for x in data if x["asset_type"] in types]
        
    def filter_search(self, data):
        value = self.params.get("search")
        if value:
            value = value.lower()
            data = [
                x for x in data
                if value in x["name"].lower()
            ]
        return data

    def filter_room(self, data):
        value = self.params.get("room")
        if value:
            data = [
                x for x in data
                if x["room"] and value.lower() in x["room"].lower()
            ]
        return data

    def filter_can_return(self, data):
        value = self.params.get("can_return")
        if value is not None:
            value = value.lower() == "true"
            data = [
                x for x in data
                if x["can_return"] == value
            ]
        return data

    def filter_pending(self, data):
        value = self.params.get("has_pending")
        if value is not None:
            value = value.lower() == "true"
            data = [
                x for x in data
                if x["has_pending_return_request"] == value
            ]
        return data


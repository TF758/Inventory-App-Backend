from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils.dateparse import parse_date
import io
from openpyxl import Workbook
from db_inventory.models import Equipment, Component, Consumable, Accessory
from django.db.models import Q

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
    
def build_site_filter(site_type, site_obj, model_class):
    """
    Returns a Q object to filter a model by site.
    """
    if site_type == 'department':
        if model_class in [Equipment, Accessory, Consumable]:
            return Q(room__location__department=site_obj)
        elif model_class == Component:
            return Q(equipment__room__location__department=site_obj)
    elif site_type == 'location':
        if model_class in [Equipment, Accessory, Consumable]:
            return Q(room__location=site_obj)
        elif model_class == Component:
            return Q(equipment__room__location=site_obj)
    elif site_type == 'room':
        if model_class in [Equipment, Accessory, Consumable]:
            return Q(room=site_obj)
        elif model_class == Component:
            return Q(equipment__room=site_obj)
    return Q()

def generate_site_asset_excel(site_obj, asset_types):
    """
    Generates an Excel workbook for a given site and requested asset types.

    Args:
        site_obj: Department, Location, or Room instance.
        asset_types: List of asset types ['equipment', 'component', 'consumable', 'accessory'].

    Returns:
        BytesIO object containing the Excel file.
    """
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    asset_model_map = {
        'equipment': {
            'model': Equipment,
            'fields': ['name', 'brand', 'model', 'serial_number', 'public_id']
        },
        'component': {
            'model': Component,
            'fields': ['name', 'brand', 'model', 'serial_number', 'quantity', 'public_id', 'equipment_id']
        },
        'consumable': {
            'model': Consumable,
            'fields': ['name', 'description', 'quantity', 'public_id', 'room_id']
        },
        'accessory': {
            'model': Accessory,
            'fields': ['name', 'serial_number', 'quantity', 'public_id', 'room_id']
        }
    }

    for asset_type in asset_types:
        asset_info = asset_model_map.get(asset_type)
        if not asset_info:
            continue

        model = asset_info['model']
        fields = asset_info['fields']

        # Build queryset
        qs = model.objects.filter(build_site_filter(site_obj._meta.model_name, site_obj, model))

        # Create sheet
        sheet = wb.create_sheet(title=asset_type.capitalize())
        sheet.append(fields)  # header row

        # Populate rows
        for obj in qs:
            row = []
            for field in fields:
                if field == 'equipment_id':
                    value = obj.equipment.public_id if getattr(obj, 'equipment', None) else ''
                elif field == 'room_id':
                    value = obj.room.public_id if getattr(obj, 'room', None) else ''
                else:
                    value = getattr(obj, field, '')
                row.append(value)
            sheet.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
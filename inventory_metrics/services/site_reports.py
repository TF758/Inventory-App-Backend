
from db_inventory.models.assets import Equipment, Accessory, Component, Consumable
from db_inventory.models.site import Department, Location, Room
from inventory_metrics.utils.viewset_helpers import build_site_filter
from django.utils import timezone


def build_site_asset_report(
    *,
    site_type: str,
    site_id: str,
    asset_types: list[str],
    generated_by=None,
) -> dict:
    site_model_map = {
        "department": Department,
        "location": Location,
        "room": Room,
    }

    asset_model_map = {
        "equipment": {
            "model": Equipment,
            "fields": ["name", "brand", "model", "serial_number", "public_id"],
        },
        "component": {
            "model": Component,
            "fields": [
                "name",
                "brand",
                "model",
                "serial_number",
                "quantity",
                "public_id",
                "equipment_id",
            ],
        },
        "consumable": {
            "model": Consumable,
            "fields": ["name", "description", "quantity", "public_id", "room_id"],
        },
        "accessory": {
            "model": Accessory,
            "fields": ["name", "serial_number", "quantity", "public_id", "room_id"],
        },
    }

    site_model = site_model_map[site_type]
    site_obj = site_model.objects.get(public_id=site_id)

    generated_at = timezone.now()

    payload = {
        "meta": {
            "site_type": site_type,
            "site_id": site_obj.public_id,
            "site_name": site_obj.name,
            "generated_by": (
                generated_by.get_username() if generated_by else "System"
            ),
            "generated_at": generated_at,
        },
        "assets": {},
        "totals": {},
    }

    for asset_type in asset_types:
        asset_info = asset_model_map.get(asset_type)
        if not asset_info:
            continue

        model = asset_info["model"]
        fields = asset_info["fields"]

        qs = model.objects.filter(
            build_site_filter(site_type, site_obj, model)
        )

        payload["totals"][asset_type] = qs.count()
        payload["assets"][asset_type] = []

        for obj in qs:
            row = {}
            for field in fields:
                if field == "equipment_id":
                    row[field] = obj.equipment.public_id if obj.equipment else None
                elif field == "room_id":
                    row[field] = obj.room.public_id if obj.room else None
                else:
                    row[field] = getattr(obj, field, None)
            payload["assets"][asset_type].append(row)

    return payload
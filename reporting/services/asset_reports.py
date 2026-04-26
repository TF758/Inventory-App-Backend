from django.utils import timezone

from assets.models.assets import Accessory, Consumable, Equipment


def build_asset_history_report(
    *,
    asset_identifier: str,
    asset_type: str,
    start_date=None,
    end_date=None,
    generated_by=None,
) -> dict:

    asset = None

    # ---------------------------------
    # Resolve Asset
    # ---------------------------------

    if asset_type == "equipment":
        asset = Equipment.objects.filter(
            public_id__iexact=asset_identifier
        ).first()

    elif asset_type == "accessory":
        asset = Accessory.objects.filter(
            public_id__iexact=asset_identifier
        ).first()

    elif asset_type == "consumable":
        asset = Consumable.objects.filter(
            public_id__iexact=asset_identifier
        ).first()

    if not asset:
        raise ValueError("Asset not found")

    events = asset.events.all()

    if start_date:
        events = events.filter(occurred_at__date__gte=start_date)

    if end_date:
        events = events.filter(occurred_at__date__lte=end_date)

    events = events.select_related("user", "reported_by").order_by("occurred_at")

    timeline = []
    summary = {}

    for event in events:
        event_type = event.event_type
        summary[event_type] = summary.get(event_type, 0) + 1

        timeline.append({
            "occurred_at": event.occurred_at,
            "event_type": event_type,
            "user": event.user.get_username() if event.user else None,
            "quantity": getattr(event, "quantity", None),
            "quantity_change": getattr(event, "quantity_change", None),
            "notes": event.notes,
            "reported_by": (
                event.reported_by.get_username()
                if event.reported_by else None
            ),
        })

    asset_info = {
        "asset_id": asset.public_id,
        "asset_type": asset_type,
        "name": asset.name,
        "room": asset.room.name if asset.room else None,
        "is_deleted": asset.is_deleted,
    }

    if asset_type == "equipment":
        asset_info.update({
            "brand": asset.brand,
            "model": asset.model,
            "serial_number": asset.serial_number,
            "status": asset.status,
        })

    elif asset_type == "accessory":
        asset_info.update({
            "serial_number": asset.serial_number,
            "quantity": asset.quantity,
        })

    elif asset_type == "consumable":
        asset_info.update({
            "description": asset.description,
            "quantity": asset.quantity,
            "low_stock_threshold": asset.low_stock_threshold,
        })

    return {
        "meta": {
            "report_name": "Asset History Report",
            "generated_at": timezone.now().isoformat(),
            "generated_by": str(generated_by) if generated_by else None,
        },
        "data": {
            "asset_identifier": asset.public_id,
            "asset_type": asset_type,
            "start_date": start_date,
            "end_date": end_date,
            "timeline_filter_applied": bool(start_date or end_date),
            "asset_information": asset_info,
            "timeline": timeline,
            "summary": summary,
        },
    }
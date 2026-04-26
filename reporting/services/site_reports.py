
from assets.models.assets import Equipment, Accessory, Component, Consumable
from sites.models.sites import Department, Location, Room
from core.models.audit import AuditLog
from django.utils import timezone
from datetime import timedelta

from analytics.utils.utils.viewset_helpers import build_site_filter


def build_site_asset_report(
    *,
    site_type: str,
    site_id: str,
    asset_types: list[str],
    generated_by=None,
) -> dict:
    """
    Build Site Asset Report payload using canonical structure:
    {
        "meta": {},
        "data": {
            "summary": {},
            "tables": {}
        }
    }
    """

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
            "fields": [
                "name",
                "description",
                "quantity",
                "public_id",
                "room_id",
            ],
        },
        "accessory": {
            "model": Accessory,
            "fields": [
                "name",
                "serial_number",
                "quantity",
                "public_id",
                "room_id",
            ],
        },
    }

    # ---------------------------------
    # Resolve Site
    # ---------------------------------
    site_model = site_model_map[site_type]
    site_obj = site_model.objects.get(public_id=site_id)

    payload = {
        "meta": {
            "report_name": "Site Asset Report",
            "site_type": site_type,
            "site_id": site_id,
            "site_name": site_obj.name,
            "generated_at": timezone.now().isoformat(),
            "generated_by": str(generated_by) if generated_by else None,
        },
        "data": {
            "summary": {},
            "tables": {},
        },
    }

    grand_total = 0

    # ---------------------------------
    # Build Tables
    # ---------------------------------
    for asset_type in asset_types:

        asset_info = asset_model_map.get(asset_type)
        if not asset_info:
            continue

        model = asset_info["model"]
        fields = asset_info["fields"]

        qs = model.objects.filter(
            build_site_filter(site_type, site_obj, model)
        )

        rows = []

        for obj in qs:
            row = {}

            for field in fields:

                if field == "equipment_id":
                    row[field] = obj.equipment.public_id if obj.equipment else None

                elif field == "room_id":
                    row[field] = obj.room.public_id if obj.room else None

                else:
                    row[field] = getattr(obj, field, None)

            rows.append(row)

        count = len(rows)
        grand_total += count

        sheet_name = asset_type.title()

        payload["data"]["summary"][f"{asset_type}_count"] = count
        payload["data"]["tables"][sheet_name] = rows

    payload["data"]["summary"]["grand_total"] = grand_total

    return payload


def build_site_audit_log_report(
    *,
    site: dict,
    audit_period_days: int,
    generated_by=None,
) -> dict:
    """
    Build Site Audit Log Report using canonical payload:
    {
        "meta": {},
        "data": {}
    }
    """

    site_filter_field_map = {
        "department": "department__public_id",
        "location": "location__public_id",
        "room": "room__public_id",
    }

    ALLOWED_PERIODS = {30, 60, 90, 120}

    EVENT_LABELS = {
        "login": "Login",
        "logout": "Logout",
        "model_created": "Created",
        "model_updated": "Updated",
        "model_deleted": "Deleted",
        "user_created": "User Created",
        "user_updated": "User Updated",
        "user_deleted": "User Deleted",
        "password_reset": "Password Reset",
        "role_assigned": "Role Assigned",
        "user_moved": "User Moved",
    }

    site_type = site["siteType"]
    site_id = site["siteId"]

    if site_type not in site_filter_field_map:
        raise ValueError("Invalid siteType")

    if audit_period_days not in ALLOWED_PERIODS:
        raise ValueError("Invalid audit_period_days")

    start_date = timezone.now() - timedelta(days=audit_period_days)
    site_filter_field = site_filter_field_map[site_type]

    logs = (
        AuditLog.objects
        .filter(**{site_filter_field: site_id}, created_at__gte=start_date)
        .select_related("user", "department", "location", "room")
        .order_by("-created_at")
    )

    rows = []

    for log in logs:
        local_time = timezone.localtime(log.created_at).replace(tzinfo=None)

        rows.append({
            "date": local_time.strftime("%Y-%m-%d"),
            "time": local_time.strftime("%H:%M:%S"),
            "action": EVENT_LABELS.get(
                log.event_type,
                log.event_type.replace("_", " ").title()
            ),
            "performed_by": log.user_email or "System",
            "affected_item_type": (
                log.target_model.replace("_", " ").title()
                if log.target_model else None
            ),
            "affected_item": log.target_name,
            "department": log.department_name,
            "location": log.location_name,
            "room": log.room_name,
            "source_ip": log.ip_address,
            "audit_reference": log.public_id,
        })

    return {
        "meta": {
            "report_name": "Site Audit Log Report",
            "site_type": site_type,
            "site_id": site_id,
            "audit_period_days": audit_period_days,
            "generated_by": str(generated_by) if generated_by else None,
            "generated_at": timezone.now().isoformat(),
        },
        "data": {
            "summary": {
                "log_count": len(rows),
                "audit_period_days": audit_period_days,
            },
            "tables": {
                "Audit Logs": rows,
            },
        },
    }

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
    Build a Site Asset Report.

    This service gathers asset data (equipment/accessories/consumables) associated with a specific site scope
    (department, location, or room). It returns structured data that can
    later be rendered into an Excel report.

    Parameters
    ----------
    site_type : str
        Scope of the report. One of:
            - department
            - location
            - room

    site_id : str
        Public ID of the site object.

    asset_types : list[str]
        Types of assets to include in the report:
            - equipment
            - component
            - consumable
            - accessory

    generated_by : User | None
        Optional user that triggered the report.
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
            "fields": ["name", "description", "quantity", "public_id", "room_id"],
        },
        "accessory": {
            "model": Accessory,
            "fields": ["name", "serial_number", "quantity", "public_id", "room_id"],
        },
    }

    site_model = site_model_map[site_type]
    site_obj = site_model.objects.get(public_id=site_id)

    payload = {
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


def build_site_audit_log_report(
    *,
    site: dict,
    audit_period_days: int,
    generated_by=None,
) -> dict:
    """
    Build a Site Audit Log Report.

    Collects audit log entries associated with a site scope
    (department, location, or room) within a given time window.

    Parameters
    ----------
    site : dict
        {
            "siteType": "department | location | room",
            "siteId": "<public_id>"
        }

    audit_period_days : int
        Time window for audit logs. Allowed values:
        30, 60, 90, 120.

    generated_by : User | None
        User who triggered the report (optional).

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
        "password_reset": "Password Reset", #nosec
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

    payload = {
        "logs": []
    }

    for log in logs:

        local_time = timezone.localtime(log.created_at).replace(tzinfo=None)

        payload["logs"].append({
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

    return payload
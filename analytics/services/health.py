from datetime import timedelta
from django.utils import timezone
from assets.models.assets import  Consumable
from django.db.models import  Sum, F
from analytics.services.snapshots import User
from assignments.models.asset_assignment import ReturnRequest
from core.utils.viewset_helpers import unallocated_users_queryset
from assets.selectors.base import accessory_queryset, consumable_queryset, equipment_queryset
from assets.selectors.consumables import low_stock_consumables_queryset
from assets.selectors.equipment import damaged_equipment_queryset, equipment_under_repair_queryset
from core.selectors.security import active_password_reset_queryset, active_sessions_queryset, forced_password_change_users_queryset, login_auditlogs_created_within_period_queryset, password_reset_events_queryset, session_created_within_period_queryset
from users.selectors.users import active_users_queryset, all_users_queryset, locked_users_queryset, system_users_queryset, users_without_active_role_queryset
from assignments.selectors.returns import pending_return_request_items_queryset, return_requests_queryset
from sites.models.sites import Department, Location, Room

def get_user_health():

    total_users = all_users_queryset().count()
    system_users = system_users_queryset().count()
    locked_users = locked_users_queryset().count()
    active_users = active_users_queryset().count()
    users_without_active_role = users_without_active_role_queryset().count()

    floating_users = unallocated_users_queryset().count()

    return {
        "total_users": total_users,
        "system_users": system_users,
        "locked_users": locked_users,
        "active_users": active_users,
        "users_without_active_role": users_without_active_role,
        "floating_users": floating_users,
    }


def get_site_structure_health():
    locations = Location.objects.all()
    rooms = Room.objects.all()

    return {
        "departments": Department.objects.count(),
        "locations": locations.count(),
        "rooms": rooms.count(),
        "unassigned_locations": locations.filter(
            department__isnull=True
        ).count(),

        "unassigned_rooms": rooms.filter(
            location__isnull=True
        ).count(),
    }


def get_asset_health():

    total_equipment = equipment_queryset().count()
    equipment_damaged = damaged_equipment_queryset().count()
    equipment_under_repair = equipment_under_repair_queryset().count()
    consumable_total_types = consumable_queryset().count()

    consumable_total_quantity = (
        Consumable.objects.aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    low_stock_consumables = low_stock_consumables_queryset().count()

    accessory_total_types = accessory_queryset().count()

    accessory_total_quantity = (
       accessory_queryset().aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    total_assets = (
        total_equipment
        + consumable_total_types
        + accessory_total_types
    )

    equipment_value = (
    equipment_queryset().aggregate(
        total=Sum("purchase_price")
    )["total"] or 0
    )

    consumable_value = (
       consumable_queryset().aggregate(
            total=Sum(F("quantity") * F("unit_cost"))
        )["total"] or 0
    )

    accessory_value = (
        accessory_queryset().aggregate(
            total=Sum(F("quantity") * F("unit_cost"))
        )["total"] or 0
    )

    total_inventory_value = (
        equipment_value
        + consumable_value
        + accessory_value
    )

    return {
        "total_assets": total_assets,

        "equipment": {
            "total": total_equipment,
            "damaged": equipment_damaged,
            "under_repair": equipment_under_repair,
        },

        "consumables": {
            "total_types": consumable_total_types,
            "total_quantity": consumable_total_quantity,
            "low_stock_count": low_stock_consumables,
        },

        "accessories": {
            "total_types": accessory_total_types,
            "total_quantity": accessory_total_quantity,
        },
        "value": {
            "equipment_value": equipment_value,
            "consumable_value": consumable_value,
            "accessory_value": accessory_value,
            "total_inventory_value": total_inventory_value,
        },
    }

def get_session_health():
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_5d = now - timedelta(days=5)

    # -------------------------
    # Core Session Metrics
    # -------------------------
    active_sessions = active_sessions_queryset().count()

    sessions_last_24h = session_created_within_period_queryset(period=last_24h).count()

    # -------------------------
    # Login Flow Metrics
    # -------------------------
    recent_logins = login_auditlogs_created_within_period_queryset(period=last_24h).count()

    unique_logins_last_5_days = login_auditlogs_created_within_period_queryset(period=last_5d).values("user").distinct().count()
    

    return {
        "active_sessions": active_sessions,
        "recent_logins": recent_logins,
        "sessions_last_24hrs": sessions_last_24h,
        "unique_logins_last_5_days": unique_logins_last_5_days,
    }

def get_security_health():
    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    # -------------------------
    # User Security Signals
    # -------------------------
    locked_users = locked_users_queryset.count()

    forced_password_change_users = forced_password_change_users_queryset.count()

    # -------------------------
    # Password Reset Signals
    # -------------------------
    active_password_resets = active_password_reset_queryset.count()

    user_initiated_resets_last_24hrs = (
        password_reset_events_queryset(
            created_after=last_24h,
            admin_initiated=False,
        ).count()
    )

    admin_initiated_resets_last_24hrs = (
        password_reset_events_queryset(
            created_after=last_24h,
            admin_initiated=True,
        ).count()
    )

    return {
        "locked_users": locked_users,
        "forced_password_change_users": forced_password_change_users,
        "active_password_resets": active_password_resets,
        "user_initiated_resets_last_24hrs": user_initiated_resets_last_24hrs,
        "admin_initiated_resets_last_24hrs": admin_initiated_resets_last_24hrs,
    }

def get_return_health():
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_3d = now - timedelta(days=3)
    last_7d = now - timedelta(days=7)

    # -------------------------
    # Backlog (current state)
    # -------------------------
    pending_requests =  return_requests_queryset( status=ReturnRequest.Status.PENDING ).count() 

    pending_items = pending_return_request_items_queryset.count()

    # -------------------------
    # Aging (VERY important)
    # -------------------------
    stale_requests_24h =  return_requests_queryset( status=ReturnRequest.Status.PENDING, requested_before=last_24h, ).count() 

    stale_requests_3d =  return_requests_queryset( status=ReturnRequest.Status.PENDING, requested_before=last_3d, ).count() 
    # -------------------------
    # Processing flow
    # -------------------------
    processed_last_24h =  return_requests_queryset( processed_after=last_24h ).count() 

    created_last_24h =  return_requests_queryset( requested_after=last_24h ).count() 
    # -------------------------
    # Quality signals
    # -------------------------
    denied_requests_last_7d = (
        return_requests_queryset(
            status=ReturnRequest.Status.DENIED,
            processed_after=last_7d,
        ).count()
    )

    partial_requests_last_7d = return_requests_queryset(
        status=ReturnRequest.Status.PARTIAL,
        processed_after=last_7d
    ).count()

    # -------------------------
    # Derived insights
    # -------------------------
    backlog_ratio = (
        pending_requests / (
            pending_requests + processed_last_24h
        )
        if (pending_requests + processed_last_24h) > 0
        else 0
    )

    return {
        "backlog": {
            "pending_requests": pending_requests,
            "pending_items": pending_items,
        },

        "aging": {
            "stale_requests_over_24h": stale_requests_24h,
            "stale_requests_over_3d": stale_requests_3d,
        },

        "flow": {
            "created_last_24h": created_last_24h,
            "processed_last_24h": processed_last_24h,
        },

        "quality": {
            "denied_requests_last_7d": denied_requests_last_7d,
            "partial_requests_last_7d": partial_requests_last_7d,
        },

        "insights": {
            "backlog_ratio": round(backlog_ratio, 2),
        }
    }
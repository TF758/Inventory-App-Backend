from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta
from datetime import date as date_type
import datetime
from assets.models.assets import Accessory, Component, Consumable, Equipment, EquipmentStatus
from db_inventory.models.security import UserSession, PasswordResetEvent
from sites.models.sites import Department, Location, Room
from db_inventory.models.audit import AuditLog
from assignments.models.asset_assignment import ReturnRequest, ReturnRequestItem
from django.contrib.auth import get_user_model
from django.db.models import F, ExpressionWrapper, DurationField, Avg, Max

from analytics.models.metrics import DailyAuthMetrics, DailyReturnMetrics, DailySystemMetrics
from analytics.models.snapshots import DailyDepartmentSnapshot


User = get_user_model()


def generate_daily_system_metrics(for_date=None):
    if for_date is None:
        for_date = timezone.localdate()  

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    base_equipment = Equipment.objects.filter(is_deleted=False)
    base_consumables = Consumable.objects.filter(is_deleted=False)
    base_accessories = Accessory.objects.filter(is_deleted=False)

    active_equipment = base_equipment.filter(
        status__in=[
            EquipmentStatus.OK,
            EquipmentStatus.UNDER_REPAIR,
            EquipmentStatus.DAMAGED,
        ]
    )

    with transaction.atomic():
        obj, created = DailySystemMetrics.objects.get_or_create(
            date=for_date,
            defaults={
                "schema_version": settings.SNAPSHOT_SCHEMA_VERSION,

                # User metrics
                "total_users": User.objects.count(),
                "human_users": User.objects.filter(is_system_user=False).count(),
                "system_users": User.objects.filter(is_system_user=True).count(),
                "active_users_last_24h": User.objects.filter(last_login__gte=last_24h).count(),
                "active_users_last_7d": User.objects.filter(last_login__gte=last_7d).count(),
                "new_users_last_24h": User.objects.filter(date_joined__gte=last_24h).count(),
                "locked_users": User.objects.filter(is_locked=True).count(),

                # Session metrics
                "total_sessions": UserSession.objects.count(),
                "active_sessions": UserSession.objects.filter(status=UserSession.Status.ACTIVE).count(),
                "revoked_sessions": UserSession.objects.filter(status=UserSession.Status.REVOKED).count(),
                "expired_sessions_last_24h": UserSession.objects.filter(
                    status=UserSession.Status.EXPIRED,
                    expires_at__gte=last_24h,
                ).count(),
                "unique_users_logged_in_last_24h": UserSession.objects.filter(
                    last_used_at__gte=last_24h
                ).values("user_id").distinct().count(),

                

                # Inventory metrics
                "total_equipment": base_equipment.count(),
                "equipment_ok": active_equipment.filter(status=EquipmentStatus.OK).count(),
                "equipment_under_repair": active_equipment.filter(status=EquipmentStatus.UNDER_REPAIR).count(),
                "equipment_damaged": active_equipment.filter(status=EquipmentStatus.DAMAGED).count(),

                "total_components": Component.objects.count(),
                "total_components_quantity": Component.objects.aggregate(total=Sum("quantity"))["total"] or 0,

               # Consumables
                "total_consumables": base_consumables.count(),
                "total_consumables_quantity": base_consumables.aggregate( total=Sum("quantity") )["total"] or 0,

                # Accessories
                "total_accessories": base_accessories.count(),
                "total_accessories_quantity": base_accessories.aggregate( total=Sum("quantity") )["total"] or 0, },)

    return created



def generate_daily_department_snapshot(
    *,
    department: Department,
    snapshot_date: date_type | None = None,
    created_by: str = "system",
) -> bool:
    """
    Generate a daily snapshot for a single department.

    Returns:
        True  -> snapshot created
        False -> snapshot already existed (skipped)
    """

    if snapshot_date is None:
        snapshot_date = timezone.localdate()

    # -------------------------------------------------
    # Base querysets (scoped once)
    # -------------------------------------------------
    rooms_qs = Room.objects.filter(location__department=department)

    equipment_qs = Equipment.objects.filter(room__in=rooms_qs, is_deleted=False)
    active_equipment_qs = equipment_qs.filter(
    status__in=[
        EquipmentStatus.OK,
        EquipmentStatus.UNDER_REPAIR,
        EquipmentStatus.DAMAGED,
        ]   
    )
    total_equipment = active_equipment_qs.count()
    components_qs = Component.objects.filter(equipment__room__in=rooms_qs)

    consumables_qs = Consumable.objects.filter( room__in=rooms_qs)

    accessories_qs = Accessory.objects.filter( room__in=rooms_qs)

    # -------------------------------------------------
    # Returns (scoped via items → room)
    # -------------------------------------------------
    return_items_qs = ReturnRequestItem.objects.filter(
        room__in=rooms_qs
    )

    request_ids = return_items_qs.values_list(
        "return_request_id",
        flat=True
    ).distinct()

    return_requests_qs = ReturnRequest.objects.filter(
        id__in=request_ids
    )

    # -------------------------------------------------
    # Users (current assignments only)
    # -------------------------------------------------
    users_qs = User.objects.filter(
        user_placements__is_current=True,
        user_placements__room__in=rooms_qs,
    ).distinct()

    total_users = users_qs.count()

    admin_roles = [
        "DEPARTMENT_ADMIN",
        "LOCATION_ADMIN",
        "ROOM_ADMIN",
        "SITE_ADMIN",
    ]

    total_admins = users_qs.filter(
        role_assignments__role__in=admin_roles
    ).filter(
        Q(role_assignments__department=department) |
        Q(role_assignments__location__department=department) |
        Q(role_assignments__room__location__department=department) |
        Q(role_assignments__role="SITE_ADMIN")
    ).distinct().count()

    total_return_requests = return_requests_qs.count()
    pending_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.PENDING ).count()
    approved_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.APPROVED ).count()
    denied_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.DENIED ).count()
    partial_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.PARTIAL ).count()

    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    returns_created_last_24h = return_requests_qs.filter( requested_at__gte=last_24h ).count()

    returns_processed_last_24h = return_requests_qs.filter( processed_at__gte=last_24h ).count()

    base_equipment = Equipment.objects.filter(is_deleted=False)

    active_equipment = base_equipment.filter(
        status__in=[
            EquipmentStatus.OK,
            EquipmentStatus.UNDER_REPAIR,
            EquipmentStatus.DAMAGED,
        ]
    )

    base_consumables = Consumable.objects.filter(is_deleted=False)
    base_accessories = Accessory.objects.filter(is_deleted=False)
        # -------------------------------------------------
        # Atomic get_or_create
    # -------------------------------------------------
    with transaction.atomic():
        obj, created = DailyDepartmentSnapshot.objects.get_or_create(
            department=department,
            snapshot_date=snapshot_date,
            defaults={
                "schema_version": settings.SNAPSHOT_SCHEMA_VERSION,
                "created_by": created_by,

                "total_users": total_users,
                "total_admins": total_admins,

                "total_locations": Location.objects.filter(
                    department=department
                ).count(),

                "total_rooms": rooms_qs.count(),

               # Inventory metrics
                "total_equipment": base_equipment.count(),
                "equipment_ok": active_equipment.filter(status=EquipmentStatus.OK).count(),
                "equipment_under_repair": active_equipment.filter(status=EquipmentStatus.UNDER_REPAIR).count(),
                "equipment_damaged": active_equipment.filter(status=EquipmentStatus.DAMAGED).count(),

                "total_components": Component.objects.count(),
                "total_components_quantity": Component.objects.aggregate( total=Sum("quantity") )["total"] or 0,

                "total_consumables": base_consumables.count(),
                "total_consumables_quantity": base_consumables.aggregate( total=Sum("quantity") )["total"] or 0,

                "total_accessories": base_accessories.count(),
                "total_accessories_quantity": base_accessories.aggregate( total=Sum("quantity") )["total"] or 0,
                # -------------------------
                # Return metrics
                # -------------------------
                "total_return_requests": total_return_requests,
                "pending_return_requests": pending_return_requests,
                "approved_return_requests": approved_return_requests,
                "denied_return_requests": denied_return_requests,
                "partial_return_requests": partial_return_requests,

                "returns_created_last_24h": returns_created_last_24h,
                "returns_processed_last_24h": returns_processed_last_24h,
            },
        )

    return created

def generate_daily_return_metrics(for_date=None):

    if for_date is None:
        for_date = timezone.localdate()

    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    with transaction.atomic():

        requests = ReturnRequest.objects.all()
        items = ReturnRequestItem.objects.all()


        processed_today = requests.filter(
            processed_at__date=for_date,
            processed_at__isnull=False
        ).annotate(
            duration=ExpressionWrapper(
                F("processed_at") - F("requested_at"),
                output_field=DurationField()
            )
        )

        duration_agg = processed_today.aggregate( avg_duration=Avg("duration"), max_duration=Max("duration"), )

        def to_seconds(value):
            return int(round(value.total_seconds())) if value else 0

        avg_seconds = to_seconds(duration_agg["avg_duration"])
        max_seconds = to_seconds(duration_agg["max_duration"])

        # -----------------------------------
        # Create snapshot
        # -----------------------------------
        obj, created = DailyReturnMetrics.objects.get_or_create(
            date=for_date,
            defaults={

                # -------------------------
                # Request-level totals
                # -------------------------
                "total_requests": requests.count(),
                "pending_requests": requests.filter( status=ReturnRequest.Status.PENDING ).count(),
                "approved_requests": requests.filter( status=ReturnRequest.Status.APPROVED ).count(),
                "denied_requests": requests.filter( status=ReturnRequest.Status.DENIED ).count(),
                "partial_requests": requests.filter( status=ReturnRequest.Status.PARTIAL ).count(),
                "completed_requests": requests.filter( status=ReturnRequest.Status.COMPLETED ).count(),

                # -------------------------
                # Activity (last 24h)
                # -------------------------
                "requests_created_last_24h": requests.filter( requested_at__gte=last_24h ).count(),

                "requests_processed_last_24h": requests.filter( processed_at__gte=last_24h ).count(),

                # -------------------------
                # Item-level
                # -------------------------
                "total_items": items.count(),
                "pending_items": items.filter( status=ReturnRequestItem.Status.PENDING ).count(),
                "approved_items": items.filter( status=ReturnRequestItem.Status.APPROVED ).count(),
                "denied_items": items.filter( status=ReturnRequestItem.Status.DENIED ).count(),
                # -------------------------
                # Type breakdown
                # -------------------------
                "equipment_items": items.filter( item_type=ReturnRequestItem.ItemType.EQUIPMENT ).count(),
                "accessory_items": items.filter( item_type=ReturnRequestItem.ItemType.ACCESSORY ).count(),
                "consumable_items": items.filter( item_type=ReturnRequestItem.ItemType.CONSUMABLE ).count(),


                "avg_processing_time_seconds": avg_seconds,
                "max_processing_time_seconds": max_seconds,

                "schema_version": settings.SNAPSHOT_SCHEMA_VERSION,
            },
        )

    return created

def generate_daily_auth_metrics(for_date=None):

    if for_date is None:
        for_date = timezone.localdate()

    now = timezone.now()

    start = timezone.make_aware(datetime.datetime.combine(for_date, datetime.datetime.min.time()))
    end = start + timedelta(days=1)

    with transaction.atomic():

        obj, created = DailyAuthMetrics.objects.get_or_create(
            date=for_date,
            defaults={

                # ------------------------
                # Login metrics
                # ------------------------
                "total_logins":
                    AuditLog.objects.filter( event_type=AuditLog.Events.LOGIN, created_at__range=(start, end) ).count(),

                "unique_users_logged_in":
                    AuditLog.objects.filter( event_type=AuditLog.Events.LOGIN, created_at__range=(start, end) ).values("user_id").distinct().count(),

                "failed_logins":
                    AuditLog.objects.filter( event_type=AuditLog.Events.LOGIN_FAILED, created_at__range=(start, end) ).count(),

                "lockouts":
                    AuditLog.objects.filter( event_type=AuditLog.Events.ACCOUNT_LOCKED, created_at__range=(start, end) ).count(),

                # ------------------------
                # Session metrics
                # ------------------------
                "active_sessions":
                    UserSession.objects.filter( status=UserSession.Status.ACTIVE ).count(),

                "revoked_sessions":
                    UserSession.objects.filter( status=UserSession.Status.REVOKED ).count(),

                "expired_sessions":
                    UserSession.objects.filter( status=UserSession.Status.EXPIRED ).count(),

                "users_multiple_active_sessions":
                    UserSession.objects.filter(
                        status=UserSession.Status.ACTIVE
                    ).values("user_id").annotate(
                        count=Count("id")
                    ).filter(
                        count__gt=1
                    ).count(),

                "users_with_revoked_sessions":
                    UserSession.objects.filter( status=UserSession.Status.REVOKED ).values("user_id").distinct().count(),

                # ------------------------
                # Password reset metrics
                # ------------------------
                "password_resets_started":
                    PasswordResetEvent.objects.filter( created_at__range=(start, end) ).count(),

                "password_resets_completed":
                    PasswordResetEvent.objects.filter( used_at__range=(start, end) ).count(),

                "active_password_resets":
                    PasswordResetEvent.objects.filter( used_at__isnull=True, expires_at__gt=now ).count(),
                "expired_password_resets":
                    PasswordResetEvent.objects.filter( used_at__isnull=True, expires_at__lt=now ).count(),
            },
        )

    return created
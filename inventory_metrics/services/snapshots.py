from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta
from datetime import date as date_type
from db_inventory.models.assets import Accessory, Component, Consumable, Equipment, EquipmentStatus
from db_inventory.models.security import UserSession
from db_inventory.models.users import PasswordResetEvent, User
from db_inventory.models.site import Department, Location, Room
from db_inventory.models.audit import AuditLog
from db_inventory.models.asset_assignment import ReturnRequest, ReturnRequestItem
from inventory_metrics.models.snapshots import DailyDepartmentSnapshot
from inventory_metrics.models.metrics import DailyAuthMetrics, DailyReturnMetrics, DailySystemMetrics
from django.contrib.auth import get_user_model
from django.db.models import F, ExpressionWrapper, DurationField, Avg, Max

User = get_user_model()


def generate_daily_system_metrics(for_date=None):
    if for_date is None:
        for_date = timezone.localdate()  

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

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
                "total_equipment": Equipment.objects.count(),
                "equipment_ok": Equipment.objects.filter(status="ok").count(),
                "equipment_under_repair": Equipment.objects.filter(status="under_repair").count(),
                "equipment_damaged": Equipment.objects.filter(status="damaged").count(),

                "total_components": Component.objects.count(),
                "total_components_quantity": Component.objects.aggregate(total=Sum("quantity"))["total"] or 0,

                "total_consumables": Consumable.objects.count(),
                "total_consumables_quantity": Consumable.objects.aggregate(total=Sum("quantity"))["total"] or 0,

                "total_accessories": Accessory.objects.count(),
                "total_accessories_quantity": Accessory.objects.aggregate(total=Sum("quantity"))["total"] or 0,
            },
        )

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

    equipment_qs = Equipment.objects.filter(room__in=rooms_qs)
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
        user_locations__is_current=True,
        user_locations__room__in=rooms_qs,
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

    total_equipment = equipment_qs.count()
    
    total_return_requests = return_requests_qs.count()
    pending_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.PENDING ).count()
    approved_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.APPROVED ).count()
    denied_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.DENIED ).count()
    partial_return_requests = return_requests_qs.filter( status=ReturnRequest.Status.PARTIAL ).count()

    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    returns_created_last_24h = return_requests_qs.filter( requested_at__gte=last_24h ).count()

    returns_processed_last_24h = return_requests_qs.filter( processed_at__gte=last_24h ).count()
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

                "total_equipment": total_equipment,
                "equipment_ok": equipment_qs.filter(
                    Q(status=EquipmentStatus.OK) | Q(status__isnull=True)
                ).count(),
                "equipment_under_repair": equipment_qs.filter(
                    status=EquipmentStatus.UNDER_REPAIR
                ).count(),
                "equipment_damaged": equipment_qs.filter(
                    status=EquipmentStatus.DAMAGED
                ).count(),

                "total_components": components_qs.count(),
                "total_components_quantity": components_qs.aggregate(
                    total=Sum("quantity")
                )["total"] or 0,

                "total_consumables": consumables_qs.count(),
                "total_consumables_quantity": consumables_qs.aggregate(
                    total=Sum("quantity")
                )["total"] or 0,

                "total_accessories": accessories_qs.count(),
                "total_accessories_quantity": accessories_qs.aggregate(
                    total=Sum("quantity")
                )["total"] or 0,
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

def generate_daily_auth_metrics(for_date=None):
    if for_date is None:
        for_date = timezone.localdate()

    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    with transaction.atomic():
        obj, created = DailyAuthMetrics.objects.get_or_create(
            date=for_date,
            defaults={
                "schema_version": settings.SNAPSHOT_SCHEMA_VERSION,

                # -----------------------------
                # Login events
                # -----------------------------
                "total_logins": AuditLog.objects.filter(
                    event_type=AuditLog.Events.LOGIN,
                    created_at__gte=last_24h,
                ).count(),

                "unique_users_logged_in": (
                    AuditLog.objects.filter(
                        event_type=AuditLog.Events.LOGIN,
                        created_at__gte=last_24h,
                        user__isnull=False,
                    )
                    .values("user_id")
                    .distinct()
                    .count()
                ),

                "failed_logins": AuditLog.objects.filter(
                    event_type=AuditLog.Events.LOGIN_FAILED,
                    created_at__gte=last_24h,
                ).count(),

                "lockouts": AuditLog.objects.filter(
                    event_type="lockout",
                    created_at__gte=last_24h,
                ).count(),

                # -----------------------------
                # Session state
                # -----------------------------
                "active_sessions": UserSession.objects.filter(
                    status=UserSession.Status.ACTIVE
                ).count(),

                "revoked_sessions": UserSession.objects.filter(
                    status=UserSession.Status.REVOKED
                ).count(),

                "expired_sessions": UserSession.objects.filter(
                    status=UserSession.Status.EXPIRED
                ).count(),

                "users_multiple_active_sessions": (
                    UserSession.objects
                    .filter(status=UserSession.Status.ACTIVE)
                    .values("user_id")
                    .annotate(c=Count("id"))
                    .filter(c__gt=1)
                    .count()
                ),

                "users_with_revoked_sessions": (
                    UserSession.objects
                    .filter(status=UserSession.Status.REVOKED)
                    .values("user_id")
                    .distinct()
                    .count()
                ),

                # -----------------------------
                # Password resets
                # -----------------------------
                "password_resets_started": PasswordResetEvent.objects.filter(
                    created_at__gte=last_24h
                ).count(),

                "password_resets_completed": PasswordResetEvent.objects.filter(
                    used_at__gte=last_24h
                ).count(),

                "active_password_resets": PasswordResetEvent.objects.filter(
                    is_active=True,
                    expires_at__gte=now,
                ).count(),

                "expired_password_resets": PasswordResetEvent.objects.filter(
                    expires_at__lt=now,
                    expires_at__gte=last_24h,
                ).count(),
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

        def to_ms(value):
            return int(value.total_seconds() * 1000) if value else 0

        avg_ms = to_ms(duration_agg["avg_duration"])
        max_ms = to_ms(duration_agg["max_duration"])

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


                "avg_processing_time_ms": avg_ms,
                "max_processing_time_ms": max_ms,

                "schema_version": settings.SNAPSHOT_SCHEMA_VERSION,
            },
        )

    return created
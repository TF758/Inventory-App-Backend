from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from datetime import date as date_type
from db_inventory.models.assets import Accessory, Component, Consumable, Equipment, EquipmentStatus
from db_inventory.models.security import UserSession
from db_inventory.models.users import User
from db_inventory.models.site import Department, Location, Room
from inventory_metrics.models.snapshots import DailyDepartmentSnapshot
from inventory_metrics.models.metrics import DailySystemMetrics
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_daily_system_metrics(for_date=None):
    if for_date is None:
        for_date = timezone.now().date()

    # Prevent double-run
    if DailySystemMetrics.objects.filter(date=for_date).exists():
        return False

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    with transaction.atomic():
        DailySystemMetrics.objects.create(
            date=for_date,
            schema_version=settings.SNAPSHOT_SCHEMA_VERSION,
           

            # User metrics
            total_users=User.objects.filter(is_system_user=False).count(),
            active_users_last_24h=User.objects.filter(last_login__gte=last_24h).count(),
            active_users_last_7d=User.objects.filter(last_login__gte=last_7d).count(),
            new_users_last_24h=User.objects.filter(date_joined__gte=last_24h).count(),
            locked_users=User.objects.filter(is_locked=True).count(),

            # Session metrics
            total_sessions=UserSession.objects.count(),
            active_sessions=UserSession.objects.filter(status=UserSession.Status.ACTIVE).count(),
            revoked_sessions=UserSession.objects.filter(status=UserSession.Status.REVOKED).count(),
            expired_sessions_last_24h=UserSession.objects.filter(
                status=UserSession.Status.EXPIRED,
                expires_at__gte=last_24h
            ).count(),
            unique_users_logged_in_last_24h=UserSession.objects.filter(
                last_used_at__gte=last_24h
            ).values("user_id").distinct().count(),

            # Inventory metrics
            total_equipment=Equipment.objects.count(),

            total_components=Component.objects.count(),
            total_components_quantity=Component.objects.aggregate(
                total=Sum("quantity")
            )["total"] or 0,

            total_consumables=Consumable.objects.count(),
            total_consumables_quantity=Consumable.objects.aggregate(
                total=Sum("quantity")
            )["total"] or 0,

            total_accessories=Accessory.objects.count(),
            total_accessories_quantity=Accessory.objects.aggregate(
                total=Sum("quantity")
            )["total"] or 0,
        )

    return True



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
    # Idempotency guard
    # -------------------------------------------------
    if DailyDepartmentSnapshot.objects.filter(
        department=department,
        snapshot_date=snapshot_date,
    ).exists():
        return False

    # -------------------------------------------------
    # Base querysets (scoped once)
    # -------------------------------------------------
    rooms_qs = Room.objects.filter(
        location__department=department
    )

    equipment_qs = Equipment.objects.filter(
        room__in=rooms_qs
    )

    components_qs = Component.objects.filter(
        equipment__room__in=rooms_qs
    )

    consumables_qs = Consumable.objects.filter(
        room__in=rooms_qs
    )

    accessories_qs = Accessory.objects.filter(
        room__in=rooms_qs
    )

    # -------------------------------------------------
    # Users (current assignments only)
    # -------------------------------------------------
    users_qs = User.objects.filter(
        user_locations__is_current=True,
        user_locations__room__in=rooms_qs,
    ).distinct()

    total_users = users_qs.count()

    # -------------------------------------------------
    # Admin users (scoped + present)
    # -------------------------------------------------
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

    # -------------------------------------------------
    # Equipment status breakdown
    # -------------------------------------------------
    total_equipment = equipment_qs.count()

    equipment_ok = equipment_qs.filter(
        Q(status=EquipmentStatus.OK) | Q(status__isnull=True)
    ).count()

    equipment_under_repair = equipment_qs.filter(
        status=EquipmentStatus.UNDER_REPAIR
    ).count()

    equipment_damaged = equipment_qs.filter(
        status=EquipmentStatus.DAMAGED
    ).count()

    # -------------------------------------------------
    # Persist snapshot atomically
    # -------------------------------------------------
    with transaction.atomic():
        DailyDepartmentSnapshot.objects.create(
            department=department,
            snapshot_date=snapshot_date,
            schema_version=settings.SNAPSHOT_SCHEMA_VERSION,
            created_by=created_by,

            total_users=total_users,
            total_admins=total_admins,

            total_locations=Location.objects.filter(
                department=department
            ).count(),

            total_rooms=rooms_qs.count(),

            total_equipment=total_equipment,
            equipment_ok=equipment_ok,
            equipment_under_repair=equipment_under_repair,
            equipment_damaged=equipment_damaged,

            total_components=components_qs.count(),
            total_components_quantity=components_qs.aggregate(
                total=Sum("quantity")
            )["total"] or 0,

            total_consumables=consumables_qs.count(),
            total_consumables_quantity=consumables_qs.aggregate(
                total=Sum("quantity")
            )["total"] or 0,

            total_accessories=accessories_qs.count(),
            total_accessories_quantity=accessories_qs.aggregate(
                total=Sum("quantity")
            )["total"] or 0,
        )

    return True
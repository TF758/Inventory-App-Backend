from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from db_inventory.models.assets import Accessory, Component, Consumable, Equipment
from db_inventory.models.security import UserSession
from db_inventory.models.users import User
from inventory_metrics.models.metrics import DailySystemMetrics


def generate_daily_system_metrics(for_date=None, created_by="celery"):
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
            created_by=created_by,

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
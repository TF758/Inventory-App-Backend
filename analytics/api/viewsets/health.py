from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from sites.models.sites import Department, Location, Room
from datetime import timedelta
from django.utils import timezone
from db_inventory.models.audit import AuditLog
from db_inventory.models.security import UserSession
from db_inventory.models.users import PasswordResetEvent
from db_inventory.models.assets import Accessory, Consumable, Equipment, EquipmentStatus
from django.db.models import Exists, OuterRef, Sum, F

from db_inventory.utils.viewset_helpers import unallocated_users_queryset
from assignments.models.asset_assignment import ReturnRequest, ReturnRequestItem
from analytics.utils.utils.viewset_helpers import get_return_health

User = get_user_model()


class HealthOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_5d = now - timedelta(days=5)

        return Response({
            "structure": {
                "departments": Department.objects.count(),
                "locations": Location.objects.count(),
                "rooms": Room.objects.count(),
            },

            "users": {
                "total_users": User.objects.count(),
                "locked_users": User.objects.filter(is_locked=True, is_system_user=False).count(),
                "users_without_active_role": User.objects.filter(
                    active_role__isnull=True,
                    is_system_user=False
                ).count(),
                "floating_users": User.objects.exclude(
                    user_placements__is_current=True
                ).filter(is_system_user=False).distinct().count(),
            },

            "sessions": {
                "active_sessions": UserSession.objects.filter(
                    status=UserSession.Status.ACTIVE
                ).count(),

                "recent_logins": AuditLog.objects.filter(
                    event_type=AuditLog.Events.LOGIN,
                    created_at__gte=last_24h
                ).count(),

                "sessions_last_24hrs": UserSession.objects.filter(
                    created_at__gte=last_24h
                ).count(),

                "unique_logins_last_5_days": (
                    AuditLog.objects.filter(
                        event_type=AuditLog.Events.LOGIN,
                        created_at__gte=last_5d
                    ).values("user").distinct().count()
                ),
            },

            "security": {
                "forced_password_change_users": User.objects.filter(
                    force_password_change=True,
                    is_system_user=False
                ).count(),

                "active_password_resets": PasswordResetEvent.objects.filter(
                    is_active=True,
                    used_at__isnull=True,
                    expires_at__gte=now,
                ).count(),

                "user_initiated_resets_last_24hrs": PasswordResetEvent.objects.filter(
                    admin__isnull=True,
                    created_at__gte=last_24h,
                ).count(),

                "admin_initiated_resets_last_24hrs": PasswordResetEvent.objects.filter(
                    admin__isnull=False,
                    created_at__gte=last_24h,
                ).count(),
            "returns": get_return_health(),
            }
        })

class SiteStructureHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        locations = Location.objects.all()
        rooms = Room.objects.all()

        return Response({
            "departments": Department.objects.count(),
            "locations": locations.count(),
            "rooms": rooms.count(),
            "unassigned_locations": locations.filter(department__isnull=True).count(),
            "unassigned_rooms": rooms.filter(location__isnull=True).count(),
        })

class UserHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        total_users = User.objects.count()

        system_users = User.objects.filter(is_system_user=True).count()

        locked_users = User.objects.filter(is_locked=True).count()

        active_users = User.objects.filter(is_active=True).count()

        users_without_active_role = User.objects.filter(
            active_role__isnull=True,
            is_system_user=False
        ).count()


        floating_users = unallocated_users_queryset().count()

        return Response({
            "total_users": total_users,
            "system_users": system_users,
            "locked_users": locked_users,
            "active_users": active_users,
            "users_without_active_role": users_without_active_role,
            "floating_users": floating_users,
        })
    
class SessionHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_5d = now - timedelta(days=5)

        # -------------------------
        # Core Session Metrics
        # -------------------------
        active_sessions = UserSession.objects.filter(
            status=UserSession.Status.ACTIVE
        ).count()

        sessions_last_24h = UserSession.objects.filter(
            created_at__gte=last_24h
        ).count()

        # -------------------------
        # Login Flow Metrics
        # -------------------------
        recent_logins = AuditLog.objects.filter(
            event_type=AuditLog.Events.LOGIN,
            created_at__gte=last_24h,
        ).count()

        unique_logins_last_5_days = (
            AuditLog.objects.filter(
                event_type=AuditLog.Events.LOGIN,
                created_at__gte=last_5d,
            )
            .values("user")
            .distinct()
            .count()
        )

        return Response({
            "active_sessions": active_sessions,
            "recent_logins": recent_logins,
            "sessions_last_24hrs": sessions_last_24h,
            "unique_logins_last_5_days": unique_logins_last_5_days,
        })
    


class SecurityHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        # -------------------------
        # User Security Signals
        # -------------------------
        locked_users = User.objects.filter(
            is_locked=True,
            is_system_user=False,
        ).count()

        forced_password_change_users = User.objects.filter(
            force_password_change=True,
            is_system_user=False,
        ).count()

        # -------------------------
        # Password Reset Signals
        # -------------------------
        active_password_resets = PasswordResetEvent.objects.filter(
            is_active=True,
            used_at__isnull=True,
            expires_at__gte=now,
        ).count()

        user_initiated_resets_last_24hrs = PasswordResetEvent.objects.filter(
            admin__isnull=True,
            created_at__gte=last_24h,
        ).count()

        admin_initiated_resets_last_24hrs = PasswordResetEvent.objects.filter(
            admin__isnull=False,
            created_at__gte=last_24h,
        ).count()

        return Response({
            "locked_users": locked_users,
            "forced_password_change_users": forced_password_change_users,
            "active_password_resets": active_password_resets,
            "user_initiated_resets_last_24hrs": user_initiated_resets_last_24hrs,
            "admin_initiated_resets_last_24hrs": admin_initiated_resets_last_24hrs,
        })


class AssetHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # -------------------------
        # Equipment
        # -------------------------
        total_equipment = Equipment.objects.count()

        equipment_damaged = Equipment.objects.filter(
            status=EquipmentStatus.DAMAGED
        ).count()

        equipment_under_repair = Equipment.objects.filter(
            status=EquipmentStatus.UNDER_REPAIR
        ).count()

        # -------------------------
        # Consumables
        # -------------------------
        consumable_total_types = Consumable.objects.count()

        consumable_total_quantity = (
            Consumable.objects.aggregate(total=Sum("quantity"))["total"] or 0
        )

        low_stock_consumables = Consumable.objects.filter(
            low_stock_threshold__gt=0,
            quantity__lte=F("low_stock_threshold"),
        ).count()

        # -------------------------
        # Accessories
        # -------------------------
        accessory_total_types = Accessory.objects.count()

        accessory_total_quantity = (
            Accessory.objects.aggregate(total=Sum("quantity"))["total"] or 0
        )

        total_assets = (
            total_equipment
            + consumable_total_types
            + accessory_total_types
        )

        return Response({
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
        })

class ReturnHealthOverviewView(APIView):
    """
    Health signals for return request workflow.

    Highlights:
    - backlog (pending requests/items)
    - delays (old unprocessed requests)
    - quality issues (denials, partials)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_3d = now - timedelta(days=3)
        last_7d = now - timedelta(days=7)

        # -------------------------
        # Backlog (current state)
        # -------------------------
        pending_requests = ReturnRequest.objects.filter( status=ReturnRequest.Status.PENDING ).count()

        pending_items = ReturnRequestItem.objects.filter( status=ReturnRequestItem.Status.PENDING ).count()

        # -------------------------
        # Aging (VERY important)
        # -------------------------
        stale_requests_24h = ReturnRequest.objects.filter(
            status=ReturnRequest.Status.PENDING,
            requested_at__lt=last_24h
        ).count()

        stale_requests_3d = ReturnRequest.objects.filter(
            status=ReturnRequest.Status.PENDING,
            requested_at__lt=last_3d
        ).count()

        # -------------------------
        # Processing flow
        # -------------------------
        processed_last_24h = ReturnRequest.objects.filter( processed_at__gte=last_24h ).count()

        created_last_24h = ReturnRequest.objects.filter( requested_at__gte=last_24h ).count()
        # -------------------------
        # Quality signals
        # -------------------------
        denied_requests_last_7d = ReturnRequest.objects.filter(
            status=ReturnRequest.Status.DENIED,
            processed_at__gte=last_7d
        ).count()

        partial_requests_last_7d = ReturnRequest.objects.filter(
            status=ReturnRequest.Status.PARTIAL,
            processed_at__gte=last_7d
        ).count()

        # -------------------------
        # Derived insights
        # -------------------------
        backlog_ratio = (
            pending_requests / (pending_requests + processed_last_24h)
            if (pending_requests + processed_last_24h) > 0 else 0
        )

        data = {
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

        return Response(data)
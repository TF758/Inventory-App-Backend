from db_inventory.models.notifications import Notification
from assignments.models.asset_assignment import EquipmentAssignment, ReturnRequest
from assets.models.assets import Accessory, Component, Consumable, Equipment, EquipmentStatus
from assets.api.serializers.accessories import AccessoryBatchWriteSerializer, AccessoryFullSerializer
from assets.api.serializers.consumables import ConsumableAreaReaSerializer, ConsumableBatchWriteSerializer
from assets.api.serializers.equipment import EquipmentBatchtWriteSerializer, EquipmentSerializer
from db_inventory.models.audit import AuditLog
from users.models.roles import RoleAssignment
from .permissions import filter_queryset_by_scope
from django.db import transaction
from collections import Counter
from django.utils.text import capfirst
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timedelta
from django.db.models import Count, Sum, Q, F, Exists, OuterRef
from django.utils import timezone
from rest_framework.response import Response
from django.conf import settings
import datetime

class ScopeFilterMixin:
    """
    Mixin to automatically filter a queryset based on the user's *active role*.
    Assumes the viewset has either:
      - a `model_class` attribute, OR
      - a `queryset` defined (from which model_class can be inferred).
    """

    model_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        model_class = self.model_class or queryset.model
        active_role = getattr(self.request.user, "active_role", None)

        if not active_role:
            return queryset.none()

        if active_role.role == "SITE_ADMIN":
            return queryset
        
        # if model_class in [Location, Department] and active_role.room:
        #     raise PermissionDenied("Room-level roles cannot access this endpoint.")
        
        # if model_class in [Department] and active_role.location:
        #     raise PermissionDenied("Location-level roles cannot access this endpoint.")

        # Only filter for list action
        if self.action == "list":
            return filter_queryset_by_scope(self.request.user, queryset, model_class)

        return queryset

class RoleVisibilityMixin:
    """
    Filters role assignments based on the viewer's active role.

    This controls *visibility*, not permission.
    Scope filtering is handled elsewhere.
    """

    def filter_visibility(self, qs):
        active = getattr(self.request.user, "active_role", None)
        if not active:
            return qs.none()

        # SITE_ADMIN sees everything
        if active.role == "SITE_ADMIN":
            return qs

        # DEPARTMENT_ADMIN:
        # - cannot see peer department admins
        if active.role == "DEPARTMENT_ADMIN":
            return qs.exclude(role="DEPARTMENT_ADMIN")

        # LOCATION_ADMIN:
        # - cannot see peer location admins
        # - cannot see department roles
        if active.role == "LOCATION_ADMIN":
            return qs.exclude(
                role__in=[
                    "DEPARTMENT_ADMIN",
                    "DEPARTMENT_VIEWER",
                    "LOCATION_ADMIN",
                ]
            )

        # ROOM_ADMIN:
        # - can only see room clerk + viewer
        if active.role == "ROOM_ADMIN":
            return qs.filter(
                role__in=[
                    "ROOM_CLERK",
                    "ROOM_VIEWER",
                ]
            )

        # Default: hide everything
        return qs.none()
    
class EquipmentBatchMixin:
    """
    Mixin to handle batch validation/import for Equipment.
    Used by EquipmentBatchValidateView and EquipmentBatchImportView.
    """

    save_to_db = False  # Override in subclasses
    header_offset = 1   # Offset because first row is header

    def process_batch(self, data):
        successes, errors = [], []

        # Count serial numbers once to detect duplicates in batch
        input_serials = [row.get("serial_number") for row in data if row.get("serial_number")]
        serial_counts = Counter(input_serials)

        for idx, row in enumerate(data):
            serializer = EquipmentBatchtWriteSerializer(data=row)
            row_number = idx + self.header_offset
            row_errors = {}

            if serializer.is_valid():
                serial_number = serializer.validated_data.get("serial_number")

                # Uniqueness check in DB
                if serial_number and Equipment.objects.filter(serial_number=serial_number).exists():
                    row_errors["serial_number"] = ["Equipment with this serial number already exists."]

                # Duplicates in same batch
                if serial_counts.get(serial_number, 0) > 1:
                    row_errors.setdefault("serial_number", []).append("Duplicate serial number in batch.")

                if row_errors:
                    errors.append({"row": row_number, "errors": row_errors})
                else:
                    if self.save_to_db:
                        obj = serializer.save()
                        successes.append({
                            "row": row_number,
                            "data": EquipmentSerializer(obj).data
                        })
                    else:
                        successes.append({
                            "row": row_number,
                            "data": serializer.validated_data
                        })
            else:
                errors.append({"row": row_number, "errors": serializer.errors})

        return successes, errors
    


class ConsumableBatchMixin:
    save_to_db = False
    header_offset = 1

    def process_batch(self, data):
        successes, errors = [], []

        for idx, row in enumerate(data):
            serializer = ConsumableBatchWriteSerializer(data=row)
            row_number = idx + self.header_offset

            if serializer.is_valid():
                if self.save_to_db:
                    obj = serializer.save()
                    successes.append({
                        "row": row_number,
                        "data": ConsumableAreaReaSerializer(obj).data
                    })
                else:
                    successes.append({
                        "row": row_number,
                        "data": serializer.validated_data
                    })
            else:
                errors.append({"row": row_number, "errors": serializer.errors})

        return successes, errors
    

class AccessoryBatchMixin:
    save_to_db = False
    header_offset = 1

    def process_batch(self, data):
        successes, errors = [], []

        # Precompute serial duplicates
        input_serials = [row.get("serial_number") for row in data if row.get("serial_number")]
        serial_counts = Counter(input_serials)

        for idx, row in enumerate(data):
            serializer = AccessoryBatchWriteSerializer(data=row)
            row_number = idx + self.header_offset
            row_errors = {}

            if serializer.is_valid():
                serial_number = serializer.validated_data.get("serial_number")

                # DB uniqueness
                if serial_number and Accessory.objects.filter(serial_number=serial_number).exists():
                    row_errors["serial_number"] = ["Accessory with this serial number already exists."]

                # Batch duplicates
                if serial_counts.get(serial_number, 0) > 1:
                    row_errors.setdefault("serial_number", []).append("Duplicate serial number in batch.")

                if row_errors:
                    errors.append({"row": row_number, "errors": row_errors})
                else:
                    if self.save_to_db:
                        obj = serializer.save()
                        successes.append({
                            "row": row_number,
                            "data": AccessoryFullSerializer(obj).data
                        })
                    else:
                        successes.append({
                            "row": row_number,
                            "data": serializer.validated_data
                        })
            else:
                errors.append({"row": row_number, "errors": serializer.errors})

        return successes, errors
    
class AuditMixin:
    """
    Mixin to record immutable audit logs for user and system actions.

    Guarantees:
    - Audit logs are only written AFTER successful DB commits
    - Works for CRUD (GenericAPIView hooks)
    - Works for explicit domain actions
    - No model-layer coupling
    """

    # -------------------------------------------------
    # Scope resolution (department → location → room)
    # -------------------------------------------------

    def _resolve_scope(self, target):
        room = location = department = None
        room_name = location_name = department_name = None

        if not target:
            return {
                "room": None,
                "room_name": None,
                "location": None,
                "location_name": None,
                "department": None,
                "department_name": None,
            }

        if hasattr(target, "room") and target.room:
            room = target.room
            room_name = room.name

            if getattr(room, "location", None):
                location = room.location
                location_name = location.name

                if getattr(location, "department", None):
                    department = location.department
                    department_name = department.name

        elif hasattr(target, "location") and target.location:
            location = target.location
            location_name = location.name

            if getattr(location, "department", None):
                department = location.department
                department_name = department.name

        elif hasattr(target, "department") and target.department:
            department = target.department
            department_name = department.name

        return {
            "room": room,
            "room_name": room_name,
            "location": location,
            "location_name": location_name,
            "department": department,
            "department_name": department_name,
        }

    def _get_target_label(self, target):
        """
        Return a human-friendly, audit-safe snapshot label.
        """
        if not target:
            return None

        if hasattr(target, "audit_label") and callable(target.audit_label):
            return target.audit_label()

        # Fallback (last resort)
        return str(target)

    def _get_target_model(self, target):
        """
        Return a human-friendly target model name.
        """
        if not target:
            return None

        return capfirst(target.__class__.__name__)

    # -------------------------------------------------
    # Core audit logger
    # -------------------------------------------------

    def _log_audit(self, event_type, *, target=None, description="", metadata=None):

        request = getattr(self, "request", None)
        user = getattr(request, "user", None) if request else None

        if user and user.is_anonymous:
            user = None

        scope = self._resolve_scope(target)

        def _create_log():
            AuditLog.objects.create(
                user=user,
                user_public_id=getattr(user, "public_id", None),
                user_email=getattr(user, "email", None),
                event_type=event_type,
                description=description,
                metadata=metadata or {},
                target_model=self._get_target_model(target),
                target_id=getattr(target, "public_id", None),
                target_name=self._get_target_label(target),
                department=scope["department"],
                department_name=scope["department_name"],
                location=scope["location"],
                location_name=scope["location_name"],
                room=scope["room"],
                room_name=scope["room_name"],
                ip_address=request.META.get("REMOTE_ADDR") if request else None,
                user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            )

        if getattr(settings, "IS_TESTING", False):
            _create_log()
        else:
            transaction.on_commit(_create_log)
        # -------------------------------------------------
        # Public helper for domain actions
        # -------------------------------------------------

    def audit(self, event_type, *, target=None, description="", metadata=None):
        """
        Public helper for explicit business/domain audits.
        """
        self._log_audit(
            event_type=event_type,
            target=target,
            description=description,
            metadata=metadata,
        )

    # -------------------------------------------------
    # DRF CRUD hooks (automatic auditing)
    # -------------------------------------------------

    def perform_create(self, serializer):
        obj = serializer.save()
        self._log_audit(
            event_type=AuditLog.Events.MODEL_CREATED,
            target=obj,
        )

    def perform_update(self, serializer):
        obj = serializer.save()
        self._log_audit(
            event_type=AuditLog.Events.MODEL_UPDATED,
            target=obj,
        )

    def perform_destroy(self, instance):
        self._log_audit(
            event_type=AuditLog.Events.MODEL_DELETED,
            target=instance,
        )
        instance.delete()

class ExcludeFiltersMixin:
    """
    Allows excluding filter fields from a filterset dynamically.
    Ensures excluded fields are removed both at runtime and from schema generation.
    """
    exclude_filter_fields: list[str] = []

    def get_filterset_class(self):
        base_class = super().get_filterset_class()
        exclude = set(self.exclude_filter_fields)

        # Dynamically subclass the base filterset
        class DynamicFilterset(base_class):
            class Meta(base_class.Meta):
                fields = {
                    k: v for k, v in base_class.Meta.fields.items()
                    if k not in exclude
                }

        return DynamicFilterset


class ListDetailSerializerMixin:
    """
    Allows a ViewSet to use different serializers for list vs detail views.
    """

    list_serializer_class = None
    detail_serializer_class = None

    def get_serializer_class(self):
        if self.action == "retrieve" and self.detail_serializer_class:
            return self.detail_serializer_class
        if self.action == "list" and self.list_serializer_class:
            return self.list_serializer_class
        return super().get_serializer_class()



class NotificationMixin:
    """
    Mixin to create user-facing notifications after successful DB commits.
    """

    def notify(
        self,
        *,
        recipient,
        notif_type,
        title,
        message,
        level=Notification.Level.INFO,
        entity=None,
        actor=None,
        meta=None,
    ):
        if not recipient or recipient.is_anonymous:
            return

        def _create_notification():
            notification = Notification.objects.create(
                recipient=recipient,
                type=notif_type,
                level=level,
                title=title,
                message=message,
                entity_type=entity.__class__.__name__.lower() if entity else None,
                entity_id=getattr(entity, "public_id", None),
                meta=meta,
            )

            # Skip websocket during tests
            if getattr(settings, "IS_TESTING", False):
                return

            channel_layer = get_channel_layer()
            if not channel_layer:
                return

            payload = {
                "public_id": notification.public_id,
                "type": notification.type,
                "level": notification.level,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "entity": {
                    "type": notification.entity_type,
                    "id": notification.entity_id,
                } if notification.entity_id else None,
                "meta": notification.meta,
            }

            async_to_sync(channel_layer.group_send)(
                f"user_{recipient.public_id}",
                {
                    "type": "notification",
                    "payload": payload,
                },
            )

        if getattr(settings, "IS_TESTING", False):
            _create_notification()
        else:
            transaction.on_commit(_create_notification)



class AccessoryDashboardMixin:
    DEFAULT_PERIOD_DAYS = 7
    MIN_PERIOD_DAYS = 1
    MAX_PERIOD_DAYS = 30

    def get_rooms(self, public_id):
        """
        Must be implemented by the concrete view.
        Should return a Room queryset.
        """
        raise NotImplementedError

    def get_period(self, request):
        try:
            period = int(
                request.query_params.get(
                    "period", self.DEFAULT_PERIOD_DAYS
                )
            )
        except ValueError:
            period = self.DEFAULT_PERIOD_DAYS

        return max(self.MIN_PERIOD_DAYS, min(period, self.MAX_PERIOD_DAYS))

    def build_dashboard_response(self, rooms, period):
        from .models import (
            Accessory,
            AccessoryAssignment,
            AccessoryEvent,
        )

        since = timezone.now() - timedelta(days=period)

        accessories_qs = Accessory.objects.filter(
            room__in=rooms,
                is_deleted=False
        )

        summary = accessories_qs.aggregate(
            accessory_types=Count("id"),
            total_quantity=Sum("quantity"),
        )

        total_quantity = summary["total_quantity"] or 0

        active_assignments_qs = AccessoryAssignment.objects.filter(
            accessory__room__in=rooms,
            accessory__is_deleted=False,
            returned_at__isnull=True
        )

        assigned_quantity = (
            active_assignments_qs.aggregate(
                total=Sum("quantity")
            )["total"] or 0
        )

        event_counts = (
            AccessoryEvent.objects.filter(
                accessory__room__in=rooms,
                accessory__is_deleted=False, 
                occurred_at__gte=since
            )
            .values("event_type")
            .annotate(count=Count("id"))
        )

        event_map = {
            row["event_type"]: row["count"]
            for row in event_counts
        }

        return {
            "summary": {
                "accessory_types": summary["accessory_types"],
                "total_quantity": total_quantity,
                "assigned_quantity": assigned_quantity,
                "unassigned_quantity": max(
                    total_quantity - assigned_quantity, 0
                ),
                "active_assignments": active_assignments_qs.count(),
            },
            "events": {
                "assigned": event_map.get("assigned", 0),
                "returned": event_map.get("returned", 0),
                "used": event_map.get("used", 0),
                "lost": event_map.get("lost", 0),
                "damaged": event_map.get("damaged", 0),
                "condemned": event_map.get("condemned", 0),
                "restocked": event_map.get("restocked", 0),
                "adjusted": event_map.get("adjusted", 0),
            },
            "meta": {
                "period_days": period,
            },
        }

class ConsumableDashboardMixin:
    DEFAULT_PERIOD_DAYS = 7
    MIN_PERIOD_DAYS = 1
    MAX_PERIOD_DAYS = 30

    def get_rooms(self, public_id):
        """
        Must be implemented by the concrete view.
        Should return a Room queryset.
        """
        raise NotImplementedError

    def get_period(self, request):
        try:
            period = int(
                request.query_params.get(
                    "period", self.DEFAULT_PERIOD_DAYS
                )
            )
        except ValueError:
            period = self.DEFAULT_PERIOD_DAYS

        return max(self.MIN_PERIOD_DAYS, min(period, self.MAX_PERIOD_DAYS))

    def build_dashboard_response(self, rooms, period):
        from .models import (
            Consumable,
            ConsumableIssue,
            ConsumableEvent,
        )

        since = timezone.now() - timedelta(days=period)

        # ─────────────────────────────
        # Inventory health (NOT time-bound)
        # ─────────────────────────────

        consumables_qs = Consumable.objects.filter(
            room__in=rooms,
                is_deleted=False
        )

        summary_base = consumables_qs.aggregate(
            consumable_types=Count("id"),
            total_quantity=Sum("quantity"),
        )

        total_quantity = summary_base["total_quantity"] or 0

        low_stock_count = consumables_qs.filter(
            quantity__lte=F("low_stock_threshold")
        ).count()

        out_of_stock_count = consumables_qs.filter(
            quantity=0
        ).count()

        # ─────────────────────────────
        # Flow / usage (time-bound)
        # ─────────────────────────────

        events_qs = ConsumableEvent.objects.filter(
            consumable__room__in=rooms,
            consumable__is_deleted=False,
            occurred_at__gte=since
        )

        # Quantity movement per event type
        event_sums = (
            events_qs
            .values("event_type")
            .annotate(
                quantity=Sum("quantity_change")
            )
        )

        event_map = {
            row["event_type"]: abs(row["quantity"] or 0)
            for row in event_sums
        }

        issued_quantity = event_map.get("issued", 0)

        return {
            "summary": {
                "consumable_types": summary_base["consumable_types"],
                "total_quantity": total_quantity,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "issued_quantity": issued_quantity,
            },
            "events": {
                "issued": event_map.get("issued", 0),
                "used": event_map.get("used", 0),
                "returned": event_map.get("returned", 0),
                "lost": event_map.get("lost", 0),
                "damaged": event_map.get("damaged", 0),
                "expired": event_map.get("expired", 0),
                "condemned": event_map.get("condemned", 0),
                "restocked": event_map.get("restocked", 0),
                "adjusted": event_map.get("adjusted", 0),
            },
            "meta": {
                "period_days": period,
            },
        }
    
class AreaDashboardMixin:

    # -------- MUST BE IMPLEMENTED --------
    def get_rooms(self, public_id):
        raise NotImplementedError

    def build_dashboard(self, obj):
        rooms = self.get_rooms(obj.public_id)

        # --------------------
        # Equipment
        # --------------------
        equipment_qs = Equipment.objects.filter(
            room__in=rooms,
            is_deleted=False
        )

        total_equipment = equipment_qs.count()

        assigned_equipment = EquipmentAssignment.objects.filter(
            equipment__room__in=rooms,
            equipment__is_deleted=False,
            returned_at__isnull=True,
        ).count()

        utilization = round(
            (assigned_equipment / total_equipment * 100)
            if total_equipment else 0,
            1,
        )

        damaged_equipment = equipment_qs.filter(
            status__in=[
                EquipmentStatus.DAMAGED,
                EquipmentStatus.UNDER_REPAIR,
            ]
        ).count()

        lost_or_condemned = equipment_qs.filter(
            status__in=[
                EquipmentStatus.LOST,
                EquipmentStatus.CONDEMNED,
            ]
        ).count()

        # --------------------
        # Consumables
        # --------------------
        consumables_qs = Consumable.objects.filter(
            room__in=rooms,
            is_deleted=False
        )

        low_stock = consumables_qs.filter(
            quantity__gt=0,
            quantity__lte=F("low_stock_threshold"),
        ).count()

        out_of_stock = consumables_qs.filter(quantity=0).count()

        accessories_qs = Accessory.objects.filter(
            room__in=rooms,
            is_deleted=False
        )

        components_qs = Component.objects.filter(
            equipment__room__in=rooms
        )

        # --------------------
        # Users & Roles
        # --------------------
        roles_qs = RoleAssignment.objects.filter(
            Q(department=obj)
            | Q(location__department=obj)
            | Q(room__location__department=obj)
            if hasattr(obj, "locations")
            else Q(location=obj)
            | Q(room__location=obj)
            if hasattr(obj, "rooms")
            else Q(room=obj)
        )

        total_users = roles_qs.values("user").distinct().count()

        admin_users = roles_qs.filter(
            role__in=[
                "SITE_ADMIN",
                "DEPARTMENT_ADMIN",
                "LOCATION_ADMIN",
                "ROOM_ADMIN",
            ]
        ).values("user").distinct().count()

        return_qs = ReturnRequest.objects.filter(
            requester__user_placements__is_current=True,
            requester__user_placements__room__in=rooms,
        ).distinct()

        pending_requests = return_qs.filter(
            status=ReturnRequest.Status.PENDING
        ).count()

        overdue_requests = return_qs.filter(
            status=ReturnRequest.Status.PENDING,
            requested_at__lte=timezone.now() - datetime.timedelta(days=7)
        ).count()

        # --------------------
        # Response
        # --------------------
        return {
            "summary": {
                "assets": {
                    "equipment": total_equipment,
                    "accessories": accessories_qs.count(),
                    "components": components_qs.count(),
                    "consumables": consumables_qs.count(),
                },
                "equipment_utilization": {
                    "assigned": assigned_equipment,
                    "total": total_equipment,
                    "percent": utilization,
                },
                "stock_risk": {
                    "low_stock_consumables": low_stock,
                    "out_of_stock_consumables": out_of_stock,
                },
                "equipment_issues": {
                    "damaged": damaged_equipment,
                    "lost_or_condemned": lost_or_condemned,
                },
                "users": {
                    "total": total_users,
                    "admins": admin_users,
                    "non_admins": max(total_users - admin_users, 0),
                },

                # 🔥 NEW (focused + meaningful)
                "returns": {
                    "pending": pending_requests,
                    "overdue": overdue_requests,
                },
            },
            "attention": {
                "damaged_equipment": damaged_equipment,
                "out_of_stock_consumables": out_of_stock,
                "low_stock_consumables": low_stock,
                "pending_returns": pending_requests,
                "overdue_returns": overdue_requests,
            },
        }

class LightEndpointMixin:
    """
    Allows a ViewSet to support a 'light' endpoint by disabling pagination
    and returning a capped queryset after filters are applied.
    """

    light_limit = 20  # default cap

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Light endpoint → no pagination + capped
        if self.pagination_class is None:
            queryset = queryset[: self.light_limit]
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # Normal paginated endpoint
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
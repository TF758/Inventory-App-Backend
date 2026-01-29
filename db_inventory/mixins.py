from db_inventory.models.security import Notification
from .permissions import filter_queryset_by_scope
from db_inventory.models import AuditLog, Equipment, Accessory
from django.db import transaction
from .serializers.equipment import EquipmentBatchtWriteSerializer,EquipmentSerializer
from .serializers.accessories import AccessoryFullSerializer, AccessoryBatchWriteSerializer
from  .serializers.consumables import ConsumableAreaReaSerializer, ConsumableBatchWriteSerializer
from collections import Counter
from django.utils.text import capfirst
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
        """
        Schedule an immutable audit log entry after transaction commit.
        """

        request = getattr(self, "request", None)
        user = getattr(request, "user", None) if request else None

        if user and user.is_anonymous:
            user = None
            
        scope = self._resolve_scope(target)

        def _create_log():
            AuditLog.objects.create(
                # Actor
                user=user,
                user_public_id=getattr(user, "public_id", None),
                user_email=getattr(user, "email", None),

                # Event
                event_type=event_type,
                description=description,
                metadata=metadata or {},

                # Target snapshot
                target_model=self._get_target_model(target),
                target_id=getattr(target, "public_id", None),
                target_name=self._get_target_label(target),

                # Scope snapshot
                department=scope["department"],
                department_name=scope["department_name"],
                location=scope["location"],
                location_name=scope["location_name"],
                room=scope["room"],
                room_name=scope["room_name"],

                # Request context
                ip_address=request.META.get("REMOTE_ADDR") if request else None,
                user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            )

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
    ):
        if not recipient or recipient.is_anonymous:
            return

        channel_layer = get_channel_layer()

        def _create_and_send(user, *, title, message, notif_type):
            notification = Notification.objects.create(
                recipient=user,
                type=notif_type,
                level=level,
                title=title,
                message=message,
                entity_type=entity.__class__.__name__.lower() if entity else None,
                entity_id=getattr(entity, "public_id", None),
            )

            payload = {
                "public_id": notification.public_id,
                "type": notification.type,
                "level": notification.level,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
            }

            group_name = f"user_{user.public_id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "notification",
                    "payload": payload,
                },
            )

        def _on_commit():
            _create_and_send(
                recipient,
                title=title,
                message=message,
                notif_type=notif_type,
            )

            # # 2️⃣ ALSO notify the actor with a generic confirmation
            # if actor and not actor.is_anonymous:
            #     _create_and_send(
            #         actor,
            #         title="Action completed",
            #         message="Your action was completed successfully.",
            #         notif_type="action_confirmation",
            #     )

        transaction.on_commit(_on_commit)
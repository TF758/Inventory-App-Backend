from rest_framework import viewsets
from .permissions import filter_queryset_by_scope
from rest_framework.exceptions import PermissionDenied
from db_inventory.models import AuditLog, Equipment, Accessory
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .serializers.equipment import EquipmentBatchtWriteSerializer,EquipmentSerializer
from .serializers.accessories import AccessoryFullSerializer, AccessoryBatchWriteSerializer
from  .serializers.consumables import ConsumableAreaReaSerializer, ConsumableBatchWriteSerializer
from collections import Counter
from django.utils import timezone


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
    Automatically logs create, update, and delete actions for ModelViewSets.
    Just add this mixin before the ModelViewSet.
    """

    def _log_audit(self, event_type, obj, description="", request=None):
        if obj is None:
            return

        user = getattr(request, "user", None)
        target_model = obj.__class__.__name__
        target_id = getattr(obj, "public_id", getattr(obj, "id", None))
        ip_address = request.META.get("REMOTE_ADDR") if request else None
        user_agent = request.META.get("HTTP_USER_AGENT") if request else None

        AuditLog.objects.create(
            user=user,
            event_type=event_type,
            target_model=target_model,
            target_id=target_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=timezone.now()
        )

    # --- Overrides for DRF ModelViewSet actions ---
    def perform_create(self, serializer):
        obj = serializer.save()
        self._log_audit(event_type=AuditLog.Events.MODEL_CREATED, obj=obj, request=self.request)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._log_audit(event_type=AuditLog.Events.MODEL_UPDATED, obj=obj, request=self.request)

    def perform_destroy(self, instance):
        self._log_audit(event_type=AuditLog.Events.MODEL_DELETED, obj=instance, request=self.request)
        instance.delete()
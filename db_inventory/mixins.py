from rest_framework import viewsets
from .permissions import filter_queryset_by_scope
from rest_framework.exceptions import PermissionDenied
from .models import Location, Department, Equipment
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .serializers.equipment import EquipmenBatchtWriteSerializer, EquipmentReadSerializer

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
        
        if model_class in [Location, Department] and active_role.room:
            raise PermissionDenied("Room-level roles cannot access this endpoint.")
        
        if model_class in [Department] and active_role.location:
            raise PermissionDenied("Location-level roles cannot access this endpoint.")

        # Only filter for list action
        if self.action == "list":
            return filter_queryset_by_scope(self.request.user, queryset, model_class)

        return queryset

class EquipmentBatchMixin:
    """
    Mixin to handle batch processing for Equipment.
    Can be used for validation-only or actual import.
    """

    save_to_db = False  # Override to True for import
    header_offset = 1   # Offset because first row is header

    def process_batch(self, data):
        successes, errors = [], []

        # Track serial numbers in input for batch duplicates
        input_serials = [row.get("serial_number") for row in data if row.get("serial_number")]

        if self.save_to_db:
            sid = transaction.savepoint()

        for idx, row in enumerate(data):
            serializer = EquipmenBatchtWriteSerializer(data=row)
            row_errors = {}

            if serializer.is_valid():
                serial_number = serializer.validated_data.get("serial_number")

                # Check uniqueness in DB
                if serial_number and Equipment.objects.filter(serial_number=serial_number).exists():
                    row_errors["serial_number"] = ["Equipment with this serial number already exists."]

                # Check duplicates within batch
                if input_serials.count(serial_number) > 1:
                    row_errors.setdefault("serial_number", []).append("Duplicate serial number in batch.")

                if row_errors:
                    errors.append({"row": idx + self.header_offset , "errors": row_errors})
                else:
                    if self.save_to_db:
                        obj = serializer.save()
                        successes.append({"row": idx + self.header_offset , "data": EquipmentReadSerializer(obj).data})
                    else:
                        successes.append({"row": idx + self.header_offset , "data": serializer.validated_data})
            else:
                errors.append({"row": idx + self.header_offset , "errors": serializer.errors})

        if self.save_to_db:
            transaction.savepoint_commit(sid)

        return successes, errors
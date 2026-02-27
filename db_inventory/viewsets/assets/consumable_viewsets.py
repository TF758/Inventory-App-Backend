from rest_framework import viewsets
from db_inventory.serializers.consumables import (
BatchConsumableHardDeleteSerializer,
BatchConsumableSoftDeleteSerializer,
ConsumableWriteSerializer,
ConsumableAreaReaSerializer
)
from db_inventory.models import Consumable, Room
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import ConsumableFilter
from django.db.models import Case, When, Value, IntegerField
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from db_inventory.pagination import FlexiblePagination
from db_inventory.mixins import ConsumableBatchMixin, AuditMixin, ScopeFilterMixin
from db_inventory.permissions import AssetPermission, is_in_scope
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from db_inventory.services.assets import hard_delete_asset, restore_asset, soft_delete_asset
from db_inventory.services.equipment_assignment import StatusChangeResult
from django.db import transaction


class ConsumableModelViewSet(AuditMixin,ScopeFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Consumable objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Consumable objects."""
    
    queryset = Consumable.objects.all().order_by('-id')
    serializer_class = ConsumableAreaReaSerializer
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]

    filterset_class = ConsumableFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ConsumableWriteSerializer
        return ConsumableAreaReaSerializer
    

    def get_queryset(self):
        qs = super().get_queryset()
        search_term = self.request.query_params.get('search', None)

        if search_term:
            # Annotate results: 1 if starts with search_term, 2 otherwise
            qs = qs.annotate(
                starts_with_order=Case(
                    When(name__istartswith=search_term, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField()
                )
            ).order_by('starts_with_order', 'name')  # starts-with results first

        return qs
    
    def perform_create(self, serializer):
            room_public_id = self.request.data.get("room")
            if not room_public_id:
                raise PermissionDenied("You must specify a room to create consumable.")
            
            # Lookup by public_id
            room = Room.objects.filter(public_id=room_public_id).first()
            if not room:
                raise PermissionDenied("Invalid room public ID.")

            active_role = getattr(self.request.user, "active_role", None)
            if not active_role:
                raise PermissionDenied("No active role assigned.")

            # Permission check
            if active_role.role != "SITE_ADMIN" and not is_in_scope(active_role, room=room):
                raise PermissionDenied("You do not have permission to create consumable in this room.")

            serializer.save(room=room)

    
class ConsumableBatchValidateView(ConsumableBatchMixin, APIView):
    save_to_db = False

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, list) else []
        if not data:
            return Response({"detail": "Expected a list of objects"}, status=status.HTTP_400_BAD_REQUEST)

        successes, errors = self.process_batch(data)

        return Response(
            {
                "validated": successes,
                "errors": errors,
                "summary": {"total": len(data), "valid": len(successes), "invalid": len(errors)},
            },
            status=status.HTTP_200_OK,
        )


class ConsumableBatchImportView(ConsumableBatchMixin, APIView):
    save_to_db = True

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, list) else []
        if not data:
            return Response({"detail": "Expected a list of objects"}, status=status.HTTP_400_BAD_REQUEST)

        successes, errors = self.process_batch(data)

        return Response(
            {
                "created": successes,
                "errors": errors,
                "summary": {"total": len(data), "success": len(successes), "failed": len(errors)},
            },
            status=status.HTTP_207_MULTI_STATUS,
        )

class ConsumableSoftDeleteView(APIView):
    """
    Soft delete a single consumable by public_id.
    """

    permission_classes = [AssetPermission]

    def delete(self, request, public_id):

        consumable = get_object_or_404(
            Consumable,
            public_id=public_id,
            is_deleted=False,
        )

        for permission in self.get_permissions():
            if hasattr(permission, "has_object_permission"):
                if not permission.has_object_permission(request, self, consumable):
                    raise PermissionDenied()

        notes = request.data.get("notes", "")

        result = soft_delete_asset(
            actor=request.user,
            asset=consumable,
            notes=notes,
            batch=False,
            now=timezone.now(),
            use_atomic=True,
            lock_asset=True,
        )

        if result == StatusChangeResult.SKIPPED:
            return Response(
                {"detail": "Consumable already deleted."},
                status=status.HTTP_200_OK,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ConsumableRestoreViewSet(APIView):
    """
    Restore a soft-deleted Consumable by public_id.
    """

    permission_classes = [AssetPermission]
    lookup_field = "public_id"

    def get(self, request, public_id=None):

        consumable = get_object_or_404(
            Consumable,
            public_id=public_id,
            is_deleted=True,
        )

        try:
            restore_asset(
                actor=request.user,
                asset=consumable,
                batch=False,
            )
        except PermissionError:
            raise PermissionDenied("Not allowed to restore consumable.")

        return Response(status=status.HTTP_200_OK)
    
class BatchConsumableSoftDeleteView(APIView):

    permission_classes = [AssetPermission]

    def post(self, request):
        serializer = BatchConsumableSoftDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consumable_public_ids = serializer.validated_data["consumable_public_ids"]
        notes = serializer.validated_data["notes"]

        actor = request.user
        now = timezone.now()

        success = skipped = failed = 0

        with transaction.atomic():

            consumable_qs = (
                Consumable.objects
                .select_for_update()
                .filter(public_id__in=consumable_public_ids)
                .order_by("id")
            )

            consumable_map = {c.public_id: c for c in consumable_qs}

            for public_id in consumable_public_ids:

                con = consumable_map.get(public_id)
                if not con:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, con)

                    result = soft_delete_asset(
                        actor=actor,
                        asset=con,
                        notes=notes,
                        batch=True,
                        now=now,
                        use_atomic=False,
                        lock_asset=False,
                    )

                    if result == StatusChangeResult.SUCCESS:
                        success += 1
                    else:
                        skipped += 1

                except PermissionError:
                    failed += 1

        return Response(
            {"success": success, "skipped": skipped, "failed": failed},
            status=status.HTTP_200_OK,
        )
class BatchConsumableHardDeleteView(APIView):

    permission_classes = [AssetPermission]

    def post(self, request):
        serializer = BatchConsumableHardDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consumable_public_ids = serializer.validated_data["consumable_public_ids"]
        notes = serializer.validated_data["notes"]

        actor = request.user
        now = timezone.now()

        success = skipped = failed = 0

        with transaction.atomic():

            consumable_qs = (
                Consumable.objects
                .select_for_update()
                .filter(public_id__in=consumable_public_ids)
                .order_by("id")
            )

            consumable_map = {c.public_id: c for c in consumable_qs}

            for public_id in consumable_public_ids:

                con = consumable_map.get(public_id)
                if not con:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, con)

                    result = hard_delete_asset(
                        actor=actor,
                        asset=con,
                        notes=notes,
                        batch=True,
                        now=now,
                        use_atomic=False,
                        lock_asset=False,
                    )

                    if result == StatusChangeResult.SUCCESS:
                        success += 1
                    else:
                        skipped += 1

                except PermissionError:
                    failed += 1

        return Response(
            {"success": success, "skipped": skipped, "failed": failed},
            status=status.HTTP_200_OK,
        )
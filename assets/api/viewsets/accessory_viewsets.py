from rest_framework import viewsets
from db_inventory.mixins import ScopeFilterMixin, AccessoryBatchMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from db_inventory.filters import AccessoryFilter
from django.db.models import Case, When, Value, IntegerField
from django.db import transaction
from assignments.services.equipment_assignment import StatusChangeResult
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db_inventory.permissions import AssetPermission
from db_inventory.mixins import AuditMixin
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from assets.api.serializers.accessories import AccessoryFullSerializer, AccessoryWriteSerializer, BatchAccessoryHardDeleteSerializer, BatchAccessorySoftDeleteSerializer
from assets.services.assets import hard_delete_asset, restore_asset, soft_delete_asset
from db_inventory.pagination import FlexiblePagination
from assets.models.assets import Accessory

class AccessoryModelViewSet(AuditMixin,ScopeFilterMixin, viewsets.ModelViewSet):

    """ViewSet for managing Accessory objects.
    This viewset provides `list`, `create`, `retrieve`, `update`, and `destroy` actions for Accessory objects."""

    queryset = Accessory.objects.all().order_by('-id')
    lookup_field = 'public_id'

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['^name', 'name']

    filterset_class = AccessoryFilter

    pagination_class = FlexiblePagination

    permission_classes = [AssetPermission]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AccessoryWriteSerializer
        return AccessoryFullSerializer
    

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
    

class AccessoryBatchValidateView(AccessoryBatchMixin, APIView):
    save_to_db = False

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, list) else []
        if not data:
            return Response(
                {"detail": "Expected a list of objects"},
                status=status.HTTP_400_BAD_REQUEST
            )

        successes, errors = self.process_batch(data)

        return Response(
            {
                "validated": successes,
                "errors": errors,
                "summary": {
                    "total": len(data),
                    "valid": len(successes),
                    "invalid": len(errors),
                },
            },
            status=status.HTTP_200_OK,
        )


class AccessoryBatchImportView(AccessoryBatchMixin, APIView):
    save_to_db = True

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, list) else []
        if not data:
            return Response(
                {"detail": "Expected a list of objects"},
                status=status.HTTP_400_BAD_REQUEST
            )

        successes, errors = self.process_batch(data)

        return Response(
            {
                "created": successes,
                "errors": errors,
                "summary": {
                    "total": len(data),
                    "success": len(successes),
                    "failed": len(errors),
                },
            },
            status=status.HTTP_207_MULTI_STATUS,
        )

class AccessorySoftDeleteView(APIView):
    """
    Soft delete a single accessory by public_id.
    """

    permission_classes = [AssetPermission]

    def delete(self, request, public_id):

        accessory = get_object_or_404(
            Accessory,
            public_id=public_id,
            is_deleted=False,
        )

        for permission in self.get_permissions():
            if hasattr(permission, "has_object_permission"):
                if not permission.has_object_permission(request, self, accessory):
                    raise PermissionDenied()

        notes = request.data.get("notes", "")

        result = soft_delete_asset(
            actor=request.user,
            asset=accessory,
            notes=notes,
            batch=False,
            now=timezone.now(),
            use_atomic=True,
            lock_asset=True,
        )

        if result == StatusChangeResult.SKIPPED:
            return Response(
                {"detail": "Accessory already deleted."},
                status=status.HTTP_200_OK,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

class AccessoryRestoreViewSet(APIView):
    """
    Restore a soft-deleted Accessory by public_id.
    """

    permission_classes = [AssetPermission]
    lookup_field = "public_id"

    def get(self, request, public_id=None):

        accessory = get_object_or_404(
            Accessory,
            public_id=public_id,
            is_deleted=True,
        )

        try:
            restore_asset(
                actor=request.user,
                asset=accessory,
                batch=False,
            )
        except PermissionError:
            raise PermissionDenied("Not allowed to restore accessory.")

        return Response(status=status.HTTP_200_OK)

class BatchAccessorySoftDeleteView(APIView):

    permission_classes = [AssetPermission]

    def post(self, request):
        serializer = BatchAccessorySoftDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessory_public_ids = serializer.validated_data["accessory_public_ids"]
        notes = serializer.validated_data["notes"]

        actor = request.user
        now = timezone.now()

        success = skipped = failed = 0

        with transaction.atomic():

            accessory_qs = (
                Accessory.objects
                .select_for_update()
                .filter(public_id__in=accessory_public_ids)
                .order_by("id")
            )

            accessory_map = {a.public_id: a for a in accessory_qs}

            for public_id in accessory_public_ids:

                acc = accessory_map.get(public_id)
                if not acc:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, acc)

                    result = soft_delete_asset(
                        actor=actor,
                        asset=acc,
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

class BatchAccessoryHardDeleteView(APIView):

    permission_classes = [AssetPermission]

    def post(self, request):
        serializer = BatchAccessoryHardDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accessory_public_ids = serializer.validated_data["accessory_public_ids"]
        notes = serializer.validated_data["notes"]

        actor = request.user
        now = timezone.now()

        success = skipped = failed = 0

        with transaction.atomic():

            accessory_qs = (
                Accessory.objects
                .select_for_update()
                .filter(public_id__in=accessory_public_ids)
                .order_by("id")
            )

            accessory_map = {a.public_id: a for a in accessory_qs}

            for public_id in accessory_public_ids:

                acc = accessory_map.get(public_id)
                if not acc:
                    failed += 1
                    continue

                try:
                    self.check_object_permissions(request, acc)

                    result = hard_delete_asset(
                        actor=actor,
                        asset=acc,
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